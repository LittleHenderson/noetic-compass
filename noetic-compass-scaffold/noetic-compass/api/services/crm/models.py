"""CRM lead domain objects — traceable value objects for the lead-capture seam.

This module is the data spine of the CRM workstream. It defines what a captured lead *is*,
and — load-bearingly — the honest distinction between a lead we have **captured locally** and
a lead we have **synced into the external CRM of record** (Airtable / HubSpot / …).

The honesty rule (mirrors ``production/billing.py``'s ``fleet_measured`` vs ``planner_estimate``)
----------------------------------------------------------------------------------------------
Capturing a lead on our own side is not the same act as landing it in the external CRM. The
load-bearing discriminator is :data:`LeadSyncStatus`:

* ``captured``     — persisted on our side, durable to us; no external landing claimed.
* ``sync_pending`` — a sync was *attempted* but the configured provider made no real landing
  (the dark/``null`` default always lands here — it is honest that nothing left the building).
* ``synced``       — confirmed landed in the external CRM, backed by a real provider
  ``external_id``. **Only a real provider may set this.** A stub never can.
* ``sync_failed``  — a real sync attempt errored. The lead is still safely captured locally;
  the failure is recorded, never swallowed.

So a prospect is never told "you're in our CRM" on the strength of a local capture alone — the
same declared-vs-verified discipline the rest of the platform runs on, applied to go-to-market.

Traceability (the spine)
------------------------
Every :class:`Lead` carries ``lead_id`` / ``created_at`` / ``version`` / ``source`` /
``trace_id`` / ``parent_ids`` so any captured lead walks back to the request that created it and
to any prior submission it descends from (a repeat submission links to its predecessor). Show
your work, or don't ship it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Mapping
from uuid import uuid4


CRM_SCHEMA_VERSION = "noetic_crm.v1"


# --------------------------------------------------------------------------
# Status vocabularies
# --------------------------------------------------------------------------

# THE load-bearing discriminator: how real a lead's external landing is. Only a real provider
# returning a genuine external id may produce ``synced`` (see ``sync.py`` / ``service.py``).
LeadSyncStatus = Literal["captured", "sync_pending", "synced", "sync_failed"]

# Pipeline stage, managed by the sales team after capture. Orthogonal to sync status: a lead
# can be ``new`` in the pipeline and ``synced`` to the CRM at the same time.
LeadPipelineStatus = Literal["new", "contacted", "qualified", "won", "lost"]


class LeadValidationError(ValueError):
    """Raised when an inbound submission is missing/!malformed (e.g. no usable email).

    Validation failures are a 4xx at the HTTP edge — the prospect's input was unusable, and we
    refuse to capture a junk record rather than persist a lead we can never contact.
    """


class CRMStateError(ValueError):
    """Raised when a transition would make a lead look more *synced* than it really is.

    The canonical case: marking a lead ``synced`` without a real provider ``external_id`` to back
    it. That is dishonesty-by-construction and is refused, not papered over.
    """


# --------------------------------------------------------------------------
# Value objects
# --------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_email(raw: str) -> str:
    """Canonicalize an email for identity/dedup: trimmed + lowercased.

    Minimal by design — not an RFC validator. :func:`LeadSubmission.validated` does the
    presence/shape check; this only canonicalizes so the same address submitted twice is
    recognised as the same person (lineage), regardless of casing/whitespace.
    """
    return raw.strip().lower()


@dataclass(frozen=True)
class LeadSubmission:
    """The raw, untrusted inbound payload from a public lead-capture form.

    This is what crosses the wire from an anonymous prospect; it is *not* yet a captured lead.
    :meth:`validated` is the gate that turns a submission into something we will persist.
    """

    email: str
    name: str = ""
    organization: str = ""
    message: str = ""
    interest: str = ""  # which offering: "cas_harness", "atlas", "platform", …
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validated(self) -> "LeadSubmission":
        """Return a normalized copy, or raise :class:`LeadValidationError`.

        The bar is deliberately low and honest: an email that is present and shaped like an
        address (one ``@`` with a dotted domain). We would rather accept a reachable lead than
        reject it on an over-strict regex; we refuse only input we could never act on.
        """
        email = self.email.strip()
        local, sep, domain = email.partition("@")
        if not sep or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise LeadValidationError(
                f"submission email {self.email!r} is not a usable address "
                f"(need local@dotted.domain); refusing to capture an uncontactable lead"
            )
        # Keep string metadata values only — a public form must not smuggle structured payloads.
        clean_meta = {str(k): str(v) for k, v in dict(self.metadata).items()}
        return LeadSubmission(
            email=email,
            name=self.name.strip(),
            organization=self.organization.strip(),
            message=self.message.strip(),
            interest=self.interest.strip(),
            metadata=clean_meta,
        )


@dataclass(frozen=True)
class CRMSyncResult:
    """The outcome of asking a :class:`~api.services.crm.sync.CRMSyncProvider` to land a lead.

    ``is_real`` is the active honesty flag: the dark/``null`` provider returns ``is_real=False``
    and ``synced=False`` (it advertises its own no-op), and only a real provider that actually
    wrote to the external CRM returns ``is_real=True`` with an ``external_id``.
    """

    provider: str  # "null" | "airtable" | "hubspot" | …
    synced: bool
    is_real: bool
    external_id: str | None = None
    synced_at: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        # Structural guard: you cannot claim a real synced landing with no external id to show.
        if self.synced and self.external_id is None:
            raise CRMStateError(
                f"provider {self.provider!r} returned synced=True with no external_id; a synced "
                f"landing must carry the CRM's record id as evidence"
            )
        if self.synced and not self.is_real:
            raise CRMStateError(
                f"provider {self.provider!r} returned synced=True but is_real=False; a stub may "
                f"never report a real landing"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "synced": self.synced,
            "is_real": self.is_real,
            "external_id": self.external_id,
            "synced_at": self.synced_at,
            "note": self.note,
        }


@dataclass(frozen=True)
class Lead:
    """A captured lead — a traceable record of record on *our* side.

    Durable to us once a durable :class:`~api.services.crm.store.LeadStore` is configured; its
    ``sync_status`` says, honestly, whether it has also reached the external CRM.
    """

    email: str  # already normalized (see normalize_email)
    lead_id: str = field(default_factory=lambda: f"lead-{uuid4().hex[:16]}")
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    version: int = 1
    source: str = "unknown"
    trace_id: str | None = None
    parent_ids: tuple[str, ...] = ()
    name: str = ""
    organization: str = ""
    message: str = ""
    interest: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)
    sync_status: LeadSyncStatus = "captured"
    pipeline_status: LeadPipelineStatus = "new"
    external_id: str | None = None
    schema_version: str = CRM_SCHEMA_VERSION

    @classmethod
    def from_submission(
        cls,
        submission: LeadSubmission,
        *,
        source: str,
        trace_id: str | None,
        parent_ids: tuple[str, ...] = (),
    ) -> "Lead":
        """Build a fresh captured lead from a *validated* submission.

        Callers must pass the output of :meth:`LeadSubmission.validated`; this stores the
        provenance (``source`` = where the form lives, ``trace_id`` = the request id) so the
        captured lead walks back to its origin.
        """
        v = submission.validated()
        return cls(
            email=normalize_email(v.email),
            source=source,
            trace_id=trace_id,
            parent_ids=tuple(parent_ids),
            name=v.name,
            organization=v.organization,
            message=v.message,
            interest=v.interest,
            metadata=dict(v.metadata),
            sync_status="captured",
        )

    def with_sync_result(self, result: CRMSyncResult) -> "Lead":
        """Return a new lead version reflecting a sync attempt's outcome (immutably).

        Honest mapping: a real landing (``result.synced``) → ``synced`` + the ``external_id``;
        a dark/no-op attempt → ``sync_pending`` (nothing left the building); a real failure →
        ``sync_failed``. The lead is never *lost* by a sync outcome — only annotated. ``version``
        bumps and ``parent_ids`` links to this record, preserving the lineage.
        """
        if result.synced:
            new_status: LeadSyncStatus = "synced"
        elif result.is_real:
            # A real provider ran and did NOT land it → an actual failure, recorded as such.
            new_status = "sync_failed"
        else:
            # Dark/null provider: a no-op by design. Honest status is "attempted, nothing landed".
            new_status = "sync_pending"
        return Lead(
            email=self.email,
            lead_id=self.lead_id,
            created_at=self.created_at,
            updated_at=_now_iso(),
            version=self.version + 1,
            source=self.source,
            trace_id=self.trace_id,
            parent_ids=self.parent_ids,
            name=self.name,
            organization=self.organization,
            message=self.message,
            interest=self.interest,
            metadata=dict(self.metadata),
            sync_status=new_status,
            pipeline_status=self.pipeline_status,
            external_id=result.external_id if result.synced else self.external_id,
            schema_version=self.schema_version,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "lead_id": self.lead_id,
            "email": self.email,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "source": self.source,
            "trace_id": self.trace_id,
            "parent_ids": list(self.parent_ids),
            "name": self.name,
            "organization": self.organization,
            "message": self.message,
            "interest": self.interest,
            "metadata": dict(self.metadata),
            "sync_status": self.sync_status,
            "pipeline_status": self.pipeline_status,
            "external_id": self.external_id,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Lead":
        """Rehydrate a lead from its ``to_dict`` form (used by the durable file store)."""
        return cls(
            email=str(data["email"]),
            lead_id=str(data["lead_id"]),
            created_at=str(data["created_at"]),
            updated_at=str(data.get("updated_at", data["created_at"])),
            version=int(data.get("version", 1)),  # type: ignore[arg-type]
            source=str(data.get("source", "unknown")),
            trace_id=(None if data.get("trace_id") is None else str(data["trace_id"])),
            parent_ids=tuple(str(p) for p in (data.get("parent_ids") or ())),  # type: ignore[union-attr]
            name=str(data.get("name", "")),
            organization=str(data.get("organization", "")),
            message=str(data.get("message", "")),
            interest=str(data.get("interest", "")),
            metadata={str(k): str(v) for k, v in dict(data.get("metadata") or {}).items()},
            sync_status=str(data.get("sync_status", "captured")),  # type: ignore[arg-type]
            pipeline_status=str(data.get("pipeline_status", "new")),  # type: ignore[arg-type]
            external_id=(None if data.get("external_id") is None else str(data["external_id"])),
            schema_version=str(data.get("schema_version", CRM_SCHEMA_VERSION)),
        )
