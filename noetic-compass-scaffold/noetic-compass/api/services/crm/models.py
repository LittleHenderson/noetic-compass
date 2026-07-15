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
``trace_id`` / ``parent_ids`` plus explicit contact consent, a pinned privacy URL, the exact
published-notice version, and an immutable server timestamp. Any captured lead walks back to the
request that created it and to any prior submission it descends from (a repeat submission links to
its predecessor). Show your work, or don't ship it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from typing import Literal, Mapping, cast
from uuid import uuid4


CRM_SCHEMA_VERSION = "noetic_crm.v2"
LEGACY_CRM_SCHEMA_VERSION = "noetic_crm.v1"
CRM_CONSENT_SCHEMA_VERSION = "noetic_crm_consent.v1"
CRM_PRIVACY_NOTICE_URL = "https://cascompass.ai/privacy"
_PRIVACY_NOTICE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


# --------------------------------------------------------------------------
# Status vocabularies
# --------------------------------------------------------------------------

# THE load-bearing discriminator: how real a lead's external landing is. Only a real provider
# returning a genuine external id may produce ``synced`` (see ``sync.py`` / ``service.py``).
LeadSyncStatus = Literal["captured", "sync_pending", "synced", "sync_failed"]

# Pipeline stage, managed by the sales team after capture. Orthogonal to sync status: a lead
# can be ``new`` in the pipeline and ``synced`` to the CRM at the same time.
LeadPipelineStatus = Literal["new", "contacted", "qualified", "won", "lost"]
VALID_PIPELINE_STATUSES: tuple[LeadPipelineStatus, ...] = (
    "new",
    "contacted",
    "qualified",
    "won",
    "lost",
)


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


def normalize_pipeline_status(raw: str) -> LeadPipelineStatus:
    """Return a canonical pipeline status or raise ``LeadValidationError``.

    The first CRM slice intentionally has a small status vocabulary. Unknown sales stages are
    refused rather than persisted as free-form text, so list/filter/report views can rely on the
    value being one of the supported stages.
    """
    status = raw.strip().lower().replace(" ", "_")
    if status not in VALID_PIPELINE_STATUSES:
        allowed = ", ".join(VALID_PIPELINE_STATUSES)
        raise LeadValidationError(
            f"pipeline_status {raw!r} is not supported; expected one of: {allowed}"
        )
    return cast(LeadPipelineStatus, status)


# --------------------------------------------------------------------------
# Value objects
# --------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _verification_now_iso() -> str:
    """Canonical whole-second UTC timestamp used by external verification receipts."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_canonical_whole_second_utc(value: object, *, field_name: str) -> str:
    """Validate an immutable evidence timestamp without accepting alternate spellings."""

    if type(value) is not str or not value:
        raise CRMStateError(f"{field_name} is required")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise CRMStateError(
            f"{field_name} must be whole-second UTC YYYY-MM-DDTHH:MM:SSZ"
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise CRMStateError(f"{field_name} must be canonical whole-second UTC")
    return value


def _normalize_privacy_notice_version(raw: object) -> str:
    """Return one explicit, log-safe published-notice version identifier."""

    if type(raw) is not str:
        raise LeadValidationError("privacy_notice_version must be a string")
    value = raw.strip()
    if _PRIVACY_NOTICE_VERSION_RE.fullmatch(value) is None:
        raise LeadValidationError(
            "privacy_notice_version must be 1-128 characters using only letters, numbers, "
            "dot, underscore, colon, or hyphen"
        )
    return value


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
    consent_to_contact: bool = False
    privacy_notice_version: str = ""

    def validated(self) -> "LeadSubmission":
        """Return a normalized copy, or raise :class:`LeadValidationError`.

        The contact-address bar is deliberately low: one ``@`` with a dotted domain. Consent is
        deliberately strict: the caller must send exact boolean ``true`` and one log-safe version
        identifier for the privacy notice actually shown. The timestamp and canonical notice URL
        are supplied later by :meth:`Lead.from_submission`, never trusted from the browser.
        """
        email = self.email.strip()
        local, sep, domain = email.partition("@")
        if not sep or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise LeadValidationError(
                f"submission email {self.email!r} is not a usable address "
                f"(need local@dotted.domain); refusing to capture an uncontactable lead"
            )
        if type(self.consent_to_contact) is not bool or self.consent_to_contact is not True:
            raise LeadValidationError(
                "consent_to_contact must be true before a public lead is persisted"
            )
        privacy_notice_version = _normalize_privacy_notice_version(
            self.privacy_notice_version
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
            consent_to_contact=True,
            privacy_notice_version=privacy_notice_version,
        )


@dataclass(frozen=True)
class CRMVerificationReceipt:
    """Secret-safe proof that the external CRM write survived strict readback.

    The receipt deliberately stores booleans, the expected lifecycle stage, a timestamp, and a
    digest of the provider responses. It never stores response bodies, URLs, credentials, or the
    lead's email/message. The digest is useful for binding a later acceptance artifact to the exact
    provider exchange without turning the local lead ledger into a second copy of CRM PII.
    """

    readback_verified: bool
    deduplicated: bool
    owner_assigned: bool
    lifecycle_stage: str
    verified_at: str
    response_digest: str
    provider: str = "airtable"

    def __post_init__(self) -> None:
        if self.provider != "airtable":
            raise CRMStateError(
                "CRM verification receipt provider must be exact 'airtable'"
            )
        for field_name, value in (
            ("readback_verified", self.readback_verified),
            ("deduplicated", self.deduplicated),
            ("owner_assigned", self.owner_assigned),
        ):
            if type(value) is not bool:
                raise CRMStateError(
                    f"CRM verification receipt {field_name} must be a boolean"
                )
            if value is not True:
                raise CRMStateError(
                    "CRM verification receipts exist only after readback, deduplication, and "
                    "owner assignment are all verified"
                )
        if (
            type(self.lifecycle_stage) is not str
            or self.lifecycle_stage not in VALID_PIPELINE_STATUSES
        ):
            allowed = ", ".join(VALID_PIPELINE_STATUSES)
            raise CRMStateError(
                "CRM verification receipt lifecycle_stage must be one exact canonical value: "
                f"{allowed}"
            )
        if type(self.verified_at) is not str or not self.verified_at:
            raise CRMStateError("CRM verification receipt requires verified_at")
        try:
            verified_at = datetime.strptime(self.verified_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise CRMStateError(
                "CRM verification receipt verified_at must be whole-second UTC "
                "YYYY-MM-DDTHH:MM:SSZ"
            ) from exc
        if verified_at.strftime("%Y-%m-%dT%H:%M:%SZ") != self.verified_at:
            raise CRMStateError(
                "CRM verification receipt verified_at must be canonical whole-second UTC"
            )
        if type(self.response_digest) is not str:
            raise CRMStateError(
                "CRM verification receipt response_digest must be sha256:<64 lowercase hex>"
            )
        prefix, separator, digest = self.response_digest.partition(":")
        if (
            separator != ":"
            or prefix != "sha256"
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise CRMStateError(
                "CRM verification receipt response_digest must be sha256:<64 lowercase hex>"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "readback_verified": self.readback_verified,
            "deduplicated": self.deduplicated,
            "owner_assigned": self.owner_assigned,
            "lifecycle_stage": self.lifecycle_stage,
            "verified_at": self.verified_at,
            "response_digest": self.response_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "CRMVerificationReceipt":
        lifecycle_stage = data.get("lifecycle_stage")
        verified_at = data.get("verified_at")
        response_digest = data.get("response_digest")
        provider = data.get("provider", "airtable")
        return cls(
            provider=provider if isinstance(provider, str) else "",
            readback_verified=data.get("readback_verified") is True,
            deduplicated=data.get("deduplicated") is True,
            owner_assigned=data.get("owner_assigned") is True,
            lifecycle_stage=lifecycle_stage if isinstance(lifecycle_stage, str) else "",
            verified_at=verified_at if isinstance(verified_at, str) else "",
            response_digest=response_digest if isinstance(response_digest, str) else "",
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
    verification_receipt: CRMVerificationReceipt | None = None

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
        if self.synced and self.provider.strip().lower() == "airtable":
            receipt = self.verification_receipt
            if receipt is None:
                raise CRMStateError(
                    "provider 'airtable' returned synced=True without a verification receipt"
                )
            if not (
                receipt.readback_verified is True
                and receipt.deduplicated is True
                and receipt.owner_assigned is True
            ):
                raise CRMStateError(
                    "provider 'airtable' returned synced=True without verified readback, "
                    "deduplication, and owner assignment"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "synced": self.synced,
            "is_real": self.is_real,
            "external_id": self.external_id,
            "synced_at": self.synced_at,
            "note": self.note,
            "verification_receipt": (
                None
                if self.verification_receipt is None
                else self.verification_receipt.to_dict()
            ),
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
    consent_to_contact: bool = False
    privacy_notice_url: str = ""
    privacy_notice_version: str = ""
    consent_recorded_at_utc: str = ""
    consent_schema_version: str = ""
    sync_status: LeadSyncStatus = "captured"
    pipeline_status: LeadPipelineStatus = "new"
    external_id: str | None = None
    verification_receipt: CRMVerificationReceipt | None = None
    schema_version: str = CRM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Keep new consent evidence complete while allowing old v1 rows to replay."""

        if self.schema_version == LEGACY_CRM_SCHEMA_VERSION:
            return
        if self.schema_version != CRM_SCHEMA_VERSION:
            raise CRMStateError(
                f"lead schema_version must be {CRM_SCHEMA_VERSION} or "
                f"{LEGACY_CRM_SCHEMA_VERSION}"
            )
        if type(self.consent_to_contact) is not bool or self.consent_to_contact is not True:
            raise CRMStateError("v2 lead requires consent_to_contact=true")
        if self.privacy_notice_url != CRM_PRIVACY_NOTICE_URL:
            raise CRMStateError(
                f"v2 lead privacy_notice_url must be exact {CRM_PRIVACY_NOTICE_URL}"
            )
        try:
            _normalize_privacy_notice_version(self.privacy_notice_version)
        except LeadValidationError as exc:
            raise CRMStateError(str(exc)) from exc
        _require_canonical_whole_second_utc(
            self.consent_recorded_at_utc,
            field_name="consent_recorded_at_utc",
        )
        if self.consent_schema_version != CRM_CONSENT_SCHEMA_VERSION:
            raise CRMStateError(
                f"v2 lead consent_schema_version must be exact {CRM_CONSENT_SCHEMA_VERSION}"
            )

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
        recorded_at = _verification_now_iso()
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
            consent_to_contact=True,
            privacy_notice_url=CRM_PRIVACY_NOTICE_URL,
            privacy_notice_version=v.privacy_notice_version,
            consent_recorded_at_utc=recorded_at,
            consent_schema_version=CRM_CONSENT_SCHEMA_VERSION,
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
            consent_to_contact=self.consent_to_contact,
            privacy_notice_url=self.privacy_notice_url,
            privacy_notice_version=self.privacy_notice_version,
            consent_recorded_at_utc=self.consent_recorded_at_utc,
            consent_schema_version=self.consent_schema_version,
            sync_status=new_status,
            pipeline_status=self.pipeline_status,
            external_id=result.external_id if result.synced else self.external_id,
            verification_receipt=(
                result.verification_receipt if result.synced else self.verification_receipt
            ),
            schema_version=self.schema_version,
        )

    def with_pipeline_status(self, pipeline_status: str) -> "Lead":
        """Return a new lead version with a sales-managed pipeline status.

        This is orthogonal to sync status: moving a lead from ``new`` to ``contacted`` must never
        make it look more externally synced than it really is. A no-op transition returns ``self``
        so repeated clicks do not bloat the append-only lead log.
        """
        normalized = normalize_pipeline_status(pipeline_status)
        if normalized == self.pipeline_status:
            return self
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
            consent_to_contact=self.consent_to_contact,
            privacy_notice_url=self.privacy_notice_url,
            privacy_notice_version=self.privacy_notice_version,
            consent_recorded_at_utc=self.consent_recorded_at_utc,
            consent_schema_version=self.consent_schema_version,
            sync_status=self.sync_status,
            pipeline_status=normalized,
            external_id=self.external_id,
            verification_receipt=self.verification_receipt,
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
            "consent_to_contact": self.consent_to_contact,
            "privacy_notice_url": self.privacy_notice_url,
            "privacy_notice_version": self.privacy_notice_version,
            "consent_recorded_at_utc": self.consent_recorded_at_utc,
            "consent_schema_version": self.consent_schema_version,
            "sync_status": self.sync_status,
            "pipeline_status": self.pipeline_status,
            "external_id": self.external_id,
            "verification_receipt": (
                None
                if self.verification_receipt is None
                else self.verification_receipt.to_dict()
            ),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Lead":
        """Rehydrate a lead from its ``to_dict`` form (used by the durable file store)."""
        raw_receipt = data.get("verification_receipt")
        if raw_receipt is None:
            verification_receipt = None
        elif isinstance(raw_receipt, Mapping):
            verification_receipt = CRMVerificationReceipt.from_dict(raw_receipt)
        else:
            raise CRMStateError(
                "persisted verification_receipt must be a JSON object or null"
            )
        schema_version = str(data.get("schema_version", LEGACY_CRM_SCHEMA_VERSION))
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
            consent_to_contact=data.get("consent_to_contact") is True,
            privacy_notice_url=str(data.get("privacy_notice_url", "")),
            privacy_notice_version=str(data.get("privacy_notice_version", "")),
            consent_recorded_at_utc=str(data.get("consent_recorded_at_utc", "")),
            consent_schema_version=str(data.get("consent_schema_version", "")),
            sync_status=str(data.get("sync_status", "captured")),  # type: ignore[arg-type]
            pipeline_status=str(data.get("pipeline_status", "new")),  # type: ignore[arg-type]
            external_id=(None if data.get("external_id") is None else str(data["external_id"])),
            verification_receipt=verification_receipt,
            schema_version=schema_version,
        )
