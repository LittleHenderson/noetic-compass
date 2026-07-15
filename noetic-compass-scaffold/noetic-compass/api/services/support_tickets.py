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
import re
import threading
from typing import Callable, Literal, Protocol
from uuid import uuid4

from api.services.crm.privacy import (
    CRM_PRIVACY_NOTICE_URL,
    CRM_PRIVACY_NOTICE_PRESENT_STATUS,
    CRMPrivacyNoticeConfigError,
    CRMPrivacyNoticeContract,
)


SUPPORT_TICKET_SCHEMA_VERSION_V1 = "cas_support_ticket.v1"
SUPPORT_TICKET_SCHEMA_VERSION = "cas_support_ticket.v2"
SUPPORT_PRIVACY_URL = CRM_PRIVACY_NOTICE_URL
SUPPORT_PRIVACY_UNAVAILABLE = "unavailable"
SupportTicketStatus = Literal["received", "routed", "acknowledged", "resolved"]


class SupportTicketValidationError(ValueError):
    """Raised when input or a requested lifecycle transition is invalid."""


class SupportTicketReplayError(SupportTicketValidationError):
    """Raised when a persisted v2 ticket fails its integrity contract."""


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
    privacy_notice_version: str
    privacy_notice_content_sha256: str
    privacy_notice_publication_status: str
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
        privacy_notice_version: str,
        privacy_notice_content_sha256: str,
        privacy_notice_publication_status: str,
        trace_id: str | None,
        now: datetime,
    ) -> "SupportTicket":
        if consent_to_contact is not True:
            raise SupportTicketValidationError(
                "consent_to_contact must be true before a support request is persisted"
            )
        try:
            notice = CRMPrivacyNoticeContract(
                publication_status=privacy_notice_publication_status,
                version=privacy_notice_version,
                content_sha256=privacy_notice_content_sha256,
                url=SUPPORT_PRIVACY_URL,
            ).validated()
        except CRMPrivacyNoticeConfigError as exc:
            raise SupportTicketValidationError(
                "support privacy notice contract must be valid before a request is persisted"
            ) from exc
        if notice.publication_status != CRM_PRIVACY_NOTICE_PRESENT_STATUS:
            raise SupportTicketValidationError(
                "support privacy notice publication status must be exact present"
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
            privacy_url=notice.url,
            privacy_notice_version=notice.version,
            privacy_notice_content_sha256=notice.content_sha256,
            privacy_notice_publication_status=notice.publication_status,
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
            "privacy_notice_version": self.privacy_notice_version,
            "privacy_notice_content_sha256": self.privacy_notice_content_sha256,
            "privacy_notice_publication_status": (
                self.privacy_notice_publication_status
            ),
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
        raw_schema_version = data.get(
            "schema_version", SUPPORT_TICKET_SCHEMA_VERSION_V1
        )
        if not isinstance(raw_schema_version, str):
            raise SupportTicketReplayError(
                "support ticket schema_version must be a string"
            )
        schema_version = raw_schema_version.strip()
        consent_to_contact = data.get("consent_to_contact", False)
        if type(consent_to_contact) is not bool:
            raise SupportTicketReplayError(
                "support ticket consent_to_contact must be a strict boolean"
            )

        if schema_version == SUPPORT_TICKET_SCHEMA_VERSION_V1:
            # v1 predates byte-bound privacy notice receipts. Keep those records readable, but
            # report the missing notice evidence honestly instead of manufacturing a v2 claim.
            privacy_url = SUPPORT_PRIVACY_URL
            privacy_notice_version = SUPPORT_PRIVACY_UNAVAILABLE
            privacy_notice_content_sha256 = ""
            privacy_notice_publication_status = SUPPORT_PRIVACY_UNAVAILABLE
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
                consent_to_contact=consent_to_contact,
                privacy_url=privacy_url,
                privacy_notice_version=privacy_notice_version,
                privacy_notice_content_sha256=privacy_notice_content_sha256,
                privacy_notice_publication_status=(
                    privacy_notice_publication_status
                ),
                trace_id=(
                    None if data.get("trace_id") is None else str(data["trace_id"])
                ),
                owner=None if data.get("owner") is None else str(data["owner"]),
                routed_at_utc=(
                    None
                    if data.get("routed_at_utc") is None
                    else str(data["routed_at_utc"])
                ),
                acknowledged_at_utc=(
                    None
                    if data.get("acknowledged_at_utc") is None
                    else str(data["acknowledged_at_utc"])
                ),
                resolved_at_utc=(
                    None
                    if data.get("resolved_at_utc") is None
                    else str(data["resolved_at_utc"])
                ),
                resolution_summary=(
                    None
                    if data.get("resolution_summary") is None
                    else str(data["resolution_summary"])
                ),
                schema_version=schema_version,
            )
        if schema_version != SUPPORT_TICKET_SCHEMA_VERSION:
            raise SupportTicketReplayError(
                f"unsupported support ticket schema_version {schema_version!r}"
            )
        if raw_schema_version != SUPPORT_TICKET_SCHEMA_VERSION:
            raise SupportTicketReplayError(
                "persisted v2 support schema_version must be exact"
            )
        return _support_ticket_from_v2(data)


_V2_FIELDS = frozenset(
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
        "privacy_notice_version",
        "privacy_notice_content_sha256",
        "privacy_notice_publication_status",
        "trace_id",
        "owner",
        "routed_at_utc",
        "acknowledged_at_utc",
        "resolved_at_utc",
        "resolution_summary",
        "schema_version",
    }
)
_SUPPORT_TICKET_ID_RE = re.compile(r"^sup_[0-9a-f]{32}$")
_V2_STATUSES: frozenset[str] = frozenset(
    {"received", "routed", "acknowledged", "resolved"}
)


def _strict_replay_string(
    data: dict[str, object], field: str, *, allow_empty: bool = False
) -> str:
    value = data.get(field)
    if not isinstance(value, str):
        raise SupportTicketReplayError(
            f"persisted v2 support {field} must be a string"
        )
    if not allow_empty and not value:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} must not be empty"
        )
    return value


def _strict_optional_replay_string(
    data: dict[str, object], field: str
) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SupportTicketReplayError(
            f"persisted v2 support {field} must be a string or null"
        )
    return value


def _strict_replay_timestamp(
    data: dict[str, object], field: str
) -> tuple[str, datetime]:
    raw = _strict_replay_string(data, field)
    try:
        parsed = _parse_utc(raw)
    except (TypeError, ValueError) as exc:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} must be a valid UTC timestamp"
        ) from exc
    if _format_utc(parsed) != raw:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} must use canonical UTC Z format"
        )
    return raw, parsed


def _strict_optional_replay_timestamp(
    data: dict[str, object], field: str
) -> tuple[str | None, datetime | None]:
    if data.get(field) is None:
        return None, None
    raw, parsed = _strict_replay_timestamp(data, field)
    return raw, parsed


def _strict_clean_replay_string(
    data: dict[str, object], field: str, *, maximum: int
) -> str:
    value = _strict_replay_string(data, field)
    try:
        cleaned = _clean_required(value, field=field, maximum=maximum)
    except SupportTicketValidationError as exc:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} is invalid"
        ) from exc
    if cleaned != value:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} is not canonically normalized"
        )
    return value


def _strict_optional_clean_replay_string(
    data: dict[str, object], field: str, *, maximum: int
) -> str | None:
    value = _strict_optional_replay_string(data, field)
    if value is None:
        return None
    try:
        cleaned = _clean_required(value, field=field, maximum=maximum)
    except SupportTicketValidationError as exc:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} is invalid"
        ) from exc
    if cleaned != value:
        raise SupportTicketReplayError(
            f"persisted v2 support {field} is not canonically normalized"
        )
    return value


def _support_ticket_from_v2(data: dict[str, object]) -> SupportTicket:
    missing = sorted(_V2_FIELDS.difference(data))
    extra = sorted(set(data).difference(_V2_FIELDS))
    if missing or extra:
        raise SupportTicketReplayError(
            "persisted v2 support ticket fields must match the exact schema"
        )

    ticket_id = _strict_replay_string(data, "ticket_id")
    if _SUPPORT_TICKET_ID_RE.fullmatch(ticket_id) is None:
        raise SupportTicketReplayError(
            "persisted v2 support ticket_id is invalid"
        )

    version_value = data["version"]
    if type(version_value) is not int or version_value < 1:
        raise SupportTicketReplayError(
            "persisted v2 support version must be a positive strict integer"
        )
    version = version_value

    status = _strict_replay_string(data, "status")
    if status not in _V2_STATUSES:
        raise SupportTicketReplayError(
            "persisted v2 support status is invalid"
        )

    created_at_utc, created_at = _strict_replay_timestamp(data, "created_at_utc")
    updated_at_utc, updated_at = _strict_replay_timestamp(data, "updated_at_utc")
    routed_at_utc, routed_at = _strict_optional_replay_timestamp(
        data, "routed_at_utc"
    )
    acknowledged_at_utc, acknowledged_at = _strict_optional_replay_timestamp(
        data, "acknowledged_at_utc"
    )
    resolved_at_utc, resolved_at = _strict_optional_replay_timestamp(
        data, "resolved_at_utc"
    )
    if updated_at < created_at:
        raise SupportTicketReplayError(
            "persisted v2 support updated_at_utc precedes created_at_utc"
        )
    for field, stamp in (
        ("routed_at_utc", routed_at),
        ("acknowledged_at_utc", acknowledged_at),
        ("resolved_at_utc", resolved_at),
    ):
        if stamp is not None and not created_at <= stamp <= updated_at:
            raise SupportTicketReplayError(
                f"persisted v2 support {field} is outside the ticket timeline"
            )

    email = _strict_replay_string(data, "email")
    try:
        if _clean_email(email) != email:
            raise SupportTicketReplayError(
                "persisted v2 support email is not canonically normalized"
            )
    except SupportTicketValidationError as exc:
        raise SupportTicketReplayError(
            "persisted v2 support email is invalid"
        ) from exc

    name = _strict_replay_string(data, "name", allow_empty=True)
    organization = _strict_replay_string(
        data, "organization", allow_empty=True
    )
    for field, value in (("name", name), ("organization", organization)):
        if len(value) > 200 or " ".join(value.split()) != value:
            raise SupportTicketReplayError(
                f"persisted v2 support {field} is invalid"
            )
    subject = _strict_clean_replay_string(data, "subject", maximum=240)
    message = _strict_clean_replay_string(data, "message", maximum=8000)
    category = _strict_clean_replay_string(data, "category", maximum=80)
    source = _strict_clean_replay_string(data, "source", maximum=120)

    consent_to_contact = data["consent_to_contact"]
    if type(consent_to_contact) is not bool or consent_to_contact is not True:
        raise SupportTicketReplayError(
            "persisted v2 support ticket requires strict consent"
        )

    privacy_url = _strict_replay_string(data, "privacy_url")
    privacy_notice_version = _strict_replay_string(
        data, "privacy_notice_version"
    )
    privacy_notice_content_sha256 = _strict_replay_string(
        data, "privacy_notice_content_sha256"
    )
    privacy_notice_publication_status = _strict_replay_string(
        data, "privacy_notice_publication_status"
    )
    try:
        notice = CRMPrivacyNoticeContract(
            publication_status=privacy_notice_publication_status,
            version=privacy_notice_version,
            content_sha256=privacy_notice_content_sha256,
            url=privacy_url,
        ).validated()
    except CRMPrivacyNoticeConfigError as exc:
        raise SupportTicketReplayError(
            "persisted v2 support privacy notice contract is invalid"
        ) from exc
    if (
        notice.publication_status != CRM_PRIVACY_NOTICE_PRESENT_STATUS
        or notice.version != privacy_notice_version
        or notice.content_sha256 != privacy_notice_content_sha256
        or notice.url != privacy_url
    ):
        raise SupportTicketReplayError(
            "persisted v2 support privacy notice contract is not exact present"
        )

    trace_id = _strict_optional_replay_string(data, "trace_id")
    owner = _strict_optional_clean_replay_string(data, "owner", maximum=200)
    resolution_summary = _strict_optional_clean_replay_string(
        data, "resolution_summary", maximum=4000
    )

    if status == "received":
        valid_lifecycle = (
            version == 1
            and updated_at == created_at
            and owner is None
            and routed_at is None
            and acknowledged_at is None
            and resolved_at is None
            and resolution_summary is None
        )
    elif status == "routed":
        valid_lifecycle = (
            version >= 2
            and owner is not None
            and routed_at is not None
            and updated_at == routed_at
            and acknowledged_at is None
            and resolved_at is None
            and resolution_summary is None
        )
    elif status == "acknowledged":
        valid_lifecycle = (
            version >= 3
            and owner is not None
            and routed_at is not None
            and acknowledged_at is not None
            and updated_at == max(routed_at, acknowledged_at)
            and resolved_at is None
            and resolution_summary is None
        )
    else:
        valid_lifecycle = (
            version >= 4
            and owner is not None
            and routed_at is not None
            and acknowledged_at is not None
            and resolved_at is not None
            and resolution_summary is not None
            and resolved_at >= max(routed_at, acknowledged_at)
            and updated_at == resolved_at
        )
    if not valid_lifecycle:
        raise SupportTicketReplayError(
            "persisted v2 support lifecycle fields contradict its status"
        )

    return SupportTicket(
        ticket_id=ticket_id,
        created_at_utc=created_at_utc,
        updated_at_utc=updated_at_utc,
        version=version,
        status=status,  # type: ignore[arg-type]
        email=email,
        name=name,
        organization=organization,
        subject=subject,
        message=message,
        category=category,
        source=source,
        consent_to_contact=True,
        privacy_url=notice.url,
        privacy_notice_version=notice.version,
        privacy_notice_content_sha256=notice.content_sha256,
        privacy_notice_publication_status=notice.publication_status,
        trace_id=trace_id,
        owner=owner,
        routed_at_utc=routed_at_utc,
        acknowledged_at_utc=acknowledged_at_utc,
        resolved_at_utc=resolved_at_utc,
        resolution_summary=resolution_summary,
        schema_version=SUPPORT_TICKET_SCHEMA_VERSION,
    )


_V2_IMMUTABLE_ATTRIBUTES = (
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


def _payload_declares_v2(payload: dict[str, object]) -> bool:
    raw = payload.get("schema_version")
    return isinstance(raw, str) and raw.strip() == SUPPORT_TICKET_SCHEMA_VERSION


def _validate_v2_history(
    current: SupportTicket | None, candidate: SupportTicket
) -> None:
    """Validate one v2 append against the prior replayed snapshot."""

    if current is None:
        if candidate.version != 1 or candidate.status != "received":
            raise SupportTicketReplayError(
                "persisted v2 support history must begin with received version 1"
            )
        return
    if (
        current.schema_version != SUPPORT_TICKET_SCHEMA_VERSION
        or candidate.schema_version != SUPPORT_TICKET_SCHEMA_VERSION
    ):
        raise SupportTicketReplayError(
            "persisted support history cannot change schema version in place"
        )
    if candidate.version == current.version:
        if candidate != current:
            raise SupportTicketReplayError(
                "persisted v2 support duplicate version has different content"
            )
        return
    if candidate.version != current.version + 1:
        raise SupportTicketReplayError(
            "persisted v2 support versions must increase exactly once per transition"
        )
    if any(
        getattr(candidate, field) != getattr(current, field)
        for field in _V2_IMMUTABLE_ATTRIBUTES
    ):
        raise SupportTicketReplayError(
            "persisted v2 support transition changed immutable ticket content"
        )

    current_updated = _parse_utc(current.updated_at_utc)
    candidate_updated = _parse_utc(candidate.updated_at_utc)
    if candidate_updated < current_updated:
        raise SupportTicketReplayError(
            "persisted v2 support transition moved updated_at_utc backwards"
        )

    transition = (current.status, candidate.status)
    valid_transition = False
    if transition == ("received", "routed"):
        valid_transition = True
    elif transition == ("routed", "routed"):
        valid_transition = (
            candidate.acknowledged_at_utc is None
            and candidate.resolved_at_utc is None
            and candidate.resolution_summary is None
        )
    elif transition == ("routed", "acknowledged"):
        valid_transition = (
            candidate.owner == current.owner
            and candidate.routed_at_utc == current.routed_at_utc
            and candidate.acknowledged_at_utc is not None
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
        raise SupportTicketReplayError(
            f"persisted v2 support lifecycle transition {transition!r} is invalid"
        )


class SupportTicketStore(Protocol):
    durable: bool

    def save(self, ticket: SupportTicket) -> SupportTicket: ...

    def get(self, ticket_id: str) -> SupportTicket | None: ...

    def list_all(self) -> list[SupportTicket]: ...


class InMemorySupportTicketStore:
    """Thread-safe non-durable test/dark store."""

    durable = False

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

    durable = True

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)
        super().__init__()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                declares_v2 = _payload_declares_v2(payload)
                try:
                    ticket = SupportTicket.from_dict(payload)
                except SupportTicketReplayError as exc:
                    if declares_v2:
                        raise SupportTicketReplayError(
                            f"invalid persisted v2 support ticket at line {line_number}"
                        ) from exc
                    continue
                except (KeyError, TypeError, ValueError) as exc:
                    if declares_v2:
                        raise SupportTicketReplayError(
                            f"invalid persisted v2 support ticket at line {line_number}"
                        ) from exc
                    continue
                current = self._records.get(ticket.ticket_id)
                if declares_v2 or (
                    current is not None
                    and current.schema_version == SUPPORT_TICKET_SCHEMA_VERSION
                ):
                    try:
                        _validate_v2_history(current, ticket)
                    except (SupportTicketReplayError, TypeError, ValueError) as exc:
                        raise SupportTicketReplayError(
                            f"invalid persisted v2 support ticket history at line {line_number}"
                        ) from exc
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

    @property
    def is_durable(self) -> bool:
        return self._store.durable

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
    # Keep process startup compatible with accounts-off/dark deployments that do not expose
    # durable support intake. The route boundary owns the security decision: in production or
    # account mode, ``_service`` refuses this non-durable store with HTTP 503 before anti-abuse
    # mutation or PII persistence. A configured path still installs the fsync-backed store.
    store: SupportTicketStore = (
        JsonlSupportTicketStore(path) if path else InMemorySupportTicketStore()
    )
    return SupportTicketService(store)
