"""Durable, tenant-scoped read-only Evidence Packet shares.

The bearer token is deliberately split from the public share identifier.  The
identifier is safe to put in a URL; the token is returned once and is accepted
only in a request header.  Durable state contains an HMAC of the token, never
the token itself.

Share records live in the owning tenant's mandatory ``StateStore`` partition.
Anonymous lookup needs one non-secret indirection because ``StateStore.get``
always requires a tenant: a system-partition locator maps the random share id to
the owning tenant.  It contains no trace id, account id, packet metadata, or
credential material.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from typing import Any, Callable, Mapping, Protocol
import uuid

from api.services.evidence_ownership import tenant_owns_trace
from api.services.production.state_substrate.interface import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)


EVIDENCE_SHARE_KIND = "evidence_packet_share"
EVIDENCE_SHARE_EVENT_KIND = "evidence_packet_share_event"
EVIDENCE_SHARE_LOCATOR_KIND = "evidence_packet_share_locator"
EVIDENCE_SHARE_LOCATOR_TENANT = "__system_evidence_share_locators__"

SHARE_SCHEMA_VERSION = "evidence_packet_share.v1"
SHARE_EVENT_SCHEMA_VERSION = "evidence_packet_share_event.v1"
SHARE_LOCATOR_SCHEMA_VERSION = "evidence_packet_share_locator.v1"
TOKEN_HASH_SCHEME = "hmac-sha256-v1"
MAX_SHARE_LIFETIME = timedelta(days=30)

_SHARE_ID_PATTERN = re.compile(r"^shr_[A-Za-z0-9_-]{20,64}$")
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
_TOKEN_DOMAIN = b"cas-harness-evidence-share-token-v1\0"


class EvidencePacketReader(Protocol):
    """The read-only repository seam used by shares (real implementation is S3/WORM)."""

    def load_packet_with_content_sha256(
        self, *, tenant_id: str, namespace: str, trace_id: str
    ) -> tuple[dict[str, Any], str]: ...


class EvidenceShareError(RuntimeError):
    """Base error for the share lifecycle."""


class EvidenceShareUnavailable(EvidenceShareError):
    """Public-safe failure: absent, invalid, expired, revoked, or unverifiable."""


class EvidenceShareNotFound(EvidenceShareError):
    """Authenticated tenant-scoped metadata/revoke lookup failed."""


class EvidenceShareConfigurationError(EvidenceShareError):
    """The service was built without a stable server-side key."""


class EvidenceShareStorageError(EvidenceShareError):
    """Durable state could not reach the requested post-condition."""


@dataclass(frozen=True, slots=True)
class EvidenceShare:
    share_id: str
    tenant_id: str
    account_id: str
    trace_id: str
    namespace: str
    packet_content_sha256: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    created_request_id_sha256: str
    revoked_request_id_sha256: str | None
    revoked_by_account_id: str | None

    def status(self, *, now: datetime) -> str:
        if self.revoked_at is not None:
            return "revoked"
        if now >= self.expires_at:
            return "expired"
        return "active"


@dataclass(frozen=True, slots=True)
class CreatedEvidenceShare:
    share: EvidenceShare
    token: str


class EvidenceShareService:
    """Create, inspect, fetch, and revoke durable packet capabilities."""

    def __init__(
        self,
        *,
        store: StateStore,
        repository: EvidencePacketReader,
        token_pepper: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        pepper = token_pepper.encode("utf-8")
        if len(pepper) < 32:
            raise EvidenceShareConfigurationError(
                "Evidence share token pepper must contain at least 32 bytes."
            )
        self.store = store
        self.repository = repository
        self._pepper = pepper
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create_share(
        self,
        *,
        tenant_id: str,
        account_id: str,
        trace_id: str,
        expires_at: datetime,
        request_id: str | None,
        namespace: str = "",
    ) -> CreatedEvidenceShare:
        tenant_id = _required_identity(tenant_id, "tenant_id")
        account_id = _required_identity(account_id, "account_id")
        trace_id = _required_identity(trace_id, "trace_id")
        now = _utc(self._clock(), "clock").replace(microsecond=0)
        expiry = _utc(expires_at, "expires_at").replace(microsecond=0)
        if expiry <= now:
            raise ValueError("expires_at must be in the future")
        if expiry > now + MAX_SHARE_LIFETIME:
            raise ValueError("expires_at may be at most 30 days in the future")
        if not tenant_owns_trace(self.store, tenant_id=tenant_id, trace_id=trace_id):
            raise EvidenceShareNotFound("Evidence Packet is unavailable.")

        try:
            packet, packet_hash = self.repository.load_packet_with_content_sha256(
                tenant_id=tenant_id,
                namespace=namespace,
                trace_id=trace_id,
            )
        except Exception as exc:
            raise EvidenceShareNotFound("Evidence Packet is unavailable.") from exc
        if (
            not isinstance(packet, dict)
            or packet.get("trace_id") != trace_id
            or not isinstance(packet_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", packet_hash)
        ):
            raise EvidenceShareNotFound("Evidence Packet is unavailable.")
        request_hash = _request_id_sha256(request_id)

        # A globally random id is created through the locator partition first.
        # A crash after that write leaves only an inert locator: without the
        # tenant share row and token hash, public fetch still fails closed.
        for _attempt in range(8):
            share_id = f"shr_{secrets.token_urlsafe(18)}"
            token = secrets.token_urlsafe(32)
            token_hash = self._token_hash(share_id=share_id, token=token)
            locator = LedgerRecord.new(
                tenant_id=EVIDENCE_SHARE_LOCATOR_TENANT,
                kind=EVIDENCE_SHARE_LOCATOR_KIND,
                record_id=share_id,
                payload={
                    "schema_version": SHARE_LOCATOR_SCHEMA_VERSION,
                    "share_id": share_id,
                    "owning_tenant_id": tenant_id,
                    "created_at": _iso(now),
                },
                source="evidence_share_locator_create",
                now=now,
            )
            try:
                stored_locator = self.store.put(locator, expected_version=0)
            except VersionConflict:
                continue
            except Exception as exc:
                raise EvidenceShareStorageError(
                    "Evidence share locator could not be persisted."
                ) from exc

            payload: dict[str, object] = {
                "schema_version": SHARE_SCHEMA_VERSION,
                "share_id": share_id,
                "account_id": account_id,
                "trace_id": trace_id,
                "namespace": namespace,
                "packet_content_sha256": packet_hash,
                "token_hash_scheme": TOKEN_HASH_SCHEME,
                "token_hash": token_hash,
                "created_at": _iso(now),
                "expires_at": _iso(expiry),
                "revoked_at": None,
                "created_request_id_sha256": request_hash,
                "revoked_request_id_sha256": None,
                "revoked_by_account_id": None,
            }
            record = LedgerRecord.new(
                tenant_id=tenant_id,
                kind=EVIDENCE_SHARE_KIND,
                record_id=share_id,
                payload=payload,
                parent_ids=(trace_id,),
                source="evidence_share_create",
                trace_id=trace_id,
                now=now,
            )
            try:
                stored = self.store.put(record, expected_version=0)
            except Exception as exc:
                self._delete_locator_best_effort(stored_locator)
                if isinstance(exc, VersionConflict):
                    continue
                raise EvidenceShareStorageError(
                    "Evidence share could not be persisted."
                ) from exc

            share = self._parse_share(stored)
            try:
                self._record_event(
                    share=share,
                    event_type="created",
                    request_id_sha256=request_hash,
                    actor_account_id=account_id,
                    occurred_at=now,
                    deterministic=True,
                )
            except Exception:
                # Never hand a live capability to the caller when its creation
                # audit could not be durably recorded.
                self._delete_locator_best_effort(stored_locator)
                self._mark_revoked_best_effort(
                    stored, now=now, request_id_sha256=request_hash
                )
                raise
            return CreatedEvidenceShare(share=share, token=token)
        raise EvidenceShareStorageError("Could not allocate a unique evidence share id.")

    def get_share(
        self,
        *,
        tenant_id: str,
        account_id: str,
        actor_role: str,
        share_id: str,
    ) -> EvidenceShare:
        tenant_id = _required_identity(tenant_id, "tenant_id")
        account_id = _required_identity(account_id, "account_id")
        _validate_share_id(share_id)
        record = self.store.get(tenant_id, EVIDENCE_SHARE_KIND, share_id)
        if record is None:
            raise EvidenceShareNotFound("Evidence share not found.")
        try:
            share = self._parse_share(record)
        except EvidenceShareUnavailable as exc:
            raise EvidenceShareNotFound("Evidence share not found.") from exc
        self._require_management_access(
            share=share, account_id=account_id, actor_role=actor_role
        )
        return share

    def revoke_share(
        self,
        *,
        tenant_id: str,
        account_id: str,
        actor_role: str,
        share_id: str,
        request_id: str | None,
    ) -> EvidenceShare:
        tenant_id = _required_identity(tenant_id, "tenant_id")
        account_id = _required_identity(account_id, "account_id")
        _validate_share_id(share_id)
        request_hash = _request_id_sha256(request_id)
        now = _utc(self._clock(), "clock").replace(microsecond=0)

        for _attempt in range(8):
            record = self.store.get(tenant_id, EVIDENCE_SHARE_KIND, share_id)
            if record is None:
                raise EvidenceShareNotFound("Evidence share not found.")
            share = self._parse_share(record)
            self._require_management_access(
                share=share, account_id=account_id, actor_role=actor_role
            )
            # Resolve the tenant-owned row before touching the global locator.
            # Otherwise a different tenant that guessed a share id could disable
            # it despite receiving a non-leaky 404.
            self._remove_locator(share_id)
            if share.revoked_at is not None:
                self._record_event(
                    share=share,
                    event_type="revoked",
                    request_id_sha256=(
                        share.revoked_request_id_sha256 or request_hash
                    ),
                    actor_account_id=share.revoked_by_account_id,
                    occurred_at=share.revoked_at,
                    deterministic=True,
                )
                return share
            payload = dict(record.payload)
            payload["revoked_at"] = _iso(now)
            payload["revoked_request_id_sha256"] = request_hash
            payload["revoked_by_account_id"] = account_id
            try:
                stored = self.store.put(
                    record.with_payload(payload, now=now),
                    expected_version=record.version,
                )
            except VersionConflict:
                continue
            except Exception as exc:
                raise EvidenceShareStorageError(
                    "Evidence share revoke could not be persisted."
                ) from exc
            revoked = self._parse_share(stored)
            self._record_event(
                share=revoked,
                event_type="revoked",
                request_id_sha256=request_hash,
                actor_account_id=account_id,
                occurred_at=now,
                deterministic=True,
            )
            return revoked
        raise EvidenceShareStorageError("Evidence share revoke conflicted repeatedly.")

    def fetch_shared_packet(
        self,
        *,
        share_id: str,
        token: str,
        request_id: str | None,
    ) -> dict[str, Any]:
        """Return immutable packet bytes through a valid active capability.

        All negative capability states deliberately collapse to
        :class:`EvidenceShareUnavailable`; the route maps that to one 404 shape.
        """

        try:
            _validate_share_id(share_id)
            if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
                raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
            locator = self.store.get(
                EVIDENCE_SHARE_LOCATOR_TENANT,
                EVIDENCE_SHARE_LOCATOR_KIND,
                share_id,
            )
            tenant_id = self._parse_locator(locator, share_id=share_id)
            record = self.store.get(tenant_id, EVIDENCE_SHARE_KIND, share_id)
            if record is None:
                raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
            share = self._parse_share(record)
            expected_hash = str(record.payload.get("token_hash") or "")
            presented_hash = self._token_hash(share_id=share_id, token=token)
            token_valid = hmac.compare_digest(expected_hash, presented_hash)
            now = _utc(self._clock(), "clock").replace(microsecond=0)
            if not token_valid or share.status(now=now) != "active":
                raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
            packet, packet_content_sha256 = (
                self.repository.load_packet_with_content_sha256(
                    tenant_id=share.tenant_id,
                    namespace=share.namespace,
                    trace_id=share.trace_id,
                )
            )
            if (
                not isinstance(packet, dict)
                or packet.get("trace_id") != share.trace_id
                or not hmac.compare_digest(
                    packet_content_sha256, share.packet_content_sha256
                )
            ):
                raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
            self._record_event(
                share=share,
                event_type="fetched",
                request_id_sha256=_request_id_sha256(request_id),
                actor_account_id=None,
                occurred_at=now,
                deterministic=False,
            )
            # The repository returns a fresh JSON mapping. Nothing in this path
            # writes packet bytes or changes the packet mapping.
            return packet
        except EvidenceShareUnavailable:
            raise
        except Exception as exc:
            # Public callers never learn whether lookup, durable state, packet
            # integrity, or audit persistence failed.
            raise EvidenceShareUnavailable(
                "Shared Evidence Packet is unavailable."
            ) from exc

    def list_events(
        self,
        *,
        tenant_id: str,
        account_id: str,
        actor_role: str,
        share_id: str,
    ) -> tuple[Mapping[str, object], ...]:
        """Tenant-scoped audit readback for tests/operator tooling."""

        self.get_share(
            tenant_id=tenant_id,
            account_id=account_id,
            actor_role=actor_role,
            share_id=share_id,
        )
        return tuple(
            record.payload
            for record in self.store.list(tenant_id, EVIDENCE_SHARE_EVENT_KIND)
            if record.payload.get("share_id") == share_id
        )

    def _token_hash(self, *, share_id: str, token: str) -> str:
        message = _TOKEN_DOMAIN + share_id.encode("ascii") + b"\0" + token.encode("ascii")
        return hmac.new(self._pepper, message, hashlib.sha256).hexdigest()

    @staticmethod
    def _require_management_access(
        *, share: EvidenceShare, account_id: str, actor_role: str
    ) -> None:
        # The StateStore tenant partition already proves same-tenant scope. A
        # second boundary prevents an unrelated member in that tenant from
        # inspecting or revoking another member's external capability.
        if share.account_id == account_id:
            return
        if str(actor_role).strip() in {"admin", "owner"}:
            return
        raise EvidenceShareNotFound("Evidence share not found.")

    def _parse_share(self, record: LedgerRecord) -> EvidenceShare:
        payload = record.payload
        if (
            record.kind != EVIDENCE_SHARE_KIND
            or payload.get("schema_version") != SHARE_SCHEMA_VERSION
            or payload.get("share_id") != record.record_id
            or payload.get("token_hash_scheme") != TOKEN_HASH_SCHEME
        ):
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        share_id = str(payload.get("share_id") or "")
        _validate_share_id(share_id)
        token_hash = str(payload.get("token_hash") or "")
        packet_hash = str(payload.get("packet_content_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", token_hash) or not re.fullmatch(
            r"[0-9a-f]{64}", packet_hash
        ):
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        account_id = _payload_text(payload, "account_id")
        trace_id = _payload_text(payload, "trace_id")
        namespace_value = payload.get("namespace")
        if not isinstance(namespace_value, str):
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        created = _parse_payload_datetime(payload, "created_at")
        expires = _parse_payload_datetime(payload, "expires_at")
        revoked = _parse_optional_payload_datetime(payload, "revoked_at")
        created_request_hash = _payload_sha256(payload, "created_request_id_sha256")
        revoked_request_value = payload.get("revoked_request_id_sha256")
        revoked_request_hash = None
        if revoked_request_value is not None:
            revoked_request_hash = _payload_sha256(
                payload, "revoked_request_id_sha256"
            )
        revoked_by_value = payload.get("revoked_by_account_id")
        revoked_by_account_id = None
        if revoked_by_value is not None:
            if not isinstance(revoked_by_value, str) or not revoked_by_value.strip():
                raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
            revoked_by_account_id = revoked_by_value.strip()
        if expires <= created or expires > created + MAX_SHARE_LIFETIME:
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        if revoked is not None and revoked < created:
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        if (revoked is None) != (
            revoked_request_hash is None and revoked_by_account_id is None
        ):
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        if record.trace_id != trace_id or tuple(record.parent_ids) != (trace_id,):
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        if _utc(record.created_at, "record.created_at").replace(microsecond=0) != created:
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        return EvidenceShare(
            share_id=share_id,
            tenant_id=record.tenant_id,
            account_id=account_id,
            trace_id=trace_id,
            namespace=namespace_value,
            packet_content_sha256=packet_hash,
            created_at=created,
            expires_at=expires,
            revoked_at=revoked,
            created_request_id_sha256=created_request_hash,
            revoked_request_id_sha256=revoked_request_hash,
            revoked_by_account_id=revoked_by_account_id,
        )

    def _parse_locator(self, record: LedgerRecord | None, *, share_id: str) -> str:
        if record is None:
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        payload = record.payload
        if (
            record.tenant_id != EVIDENCE_SHARE_LOCATOR_TENANT
            or record.kind != EVIDENCE_SHARE_LOCATOR_KIND
            or record.record_id != share_id
            or payload.get("schema_version") != SHARE_LOCATOR_SCHEMA_VERSION
            or payload.get("share_id") != share_id
        ):
            raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
        return _payload_text(payload, "owning_tenant_id")

    def _record_event(
        self,
        *,
        share: EvidenceShare,
        event_type: str,
        request_id_sha256: str,
        actor_account_id: str | None,
        occurred_at: datetime,
        deterministic: bool,
    ) -> None:
        if event_type not in {"created", "fetched", "revoked"}:
            raise ValueError("unknown evidence share event")
        suffix = event_type if deterministic else f"fetched-{uuid.uuid4().hex}"
        event_id = f"{share.share_id}-{suffix}"
        payload: dict[str, object] = {
            "schema_version": SHARE_EVENT_SCHEMA_VERSION,
            "event_id": event_id,
            "event_type": event_type,
            "share_id": share.share_id,
            "trace_id": share.trace_id,
            "occurred_at": _iso(occurred_at),
            "request_id_sha256": request_id_sha256,
            "actor_account_id": actor_account_id,
            "packet_content_sha256": share.packet_content_sha256,
        }
        record = LedgerRecord.new(
            tenant_id=share.tenant_id,
            kind=EVIDENCE_SHARE_EVENT_KIND,
            record_id=event_id,
            payload=payload,
            parent_ids=(share.share_id, share.trace_id),
            source=f"evidence_share_{event_type}",
            trace_id=share.trace_id,
            now=occurred_at,
        )
        try:
            self.store.put(record, expected_version=0)
        except VersionConflict:
            if not deterministic:
                raise EvidenceShareStorageError(
                    "Evidence share fetch audit id conflicted."
                )
            existing = self.store.get(
                share.tenant_id, EVIDENCE_SHARE_EVENT_KIND, event_id
            )
            if existing is None or dict(existing.payload) != payload:
                raise EvidenceShareStorageError(
                    "Evidence share audit event conflicted."
                )
        except Exception as exc:
            raise EvidenceShareStorageError(
                "Evidence share audit event could not be persisted."
            ) from exc

    def _remove_locator(self, share_id: str) -> None:
        for _attempt in range(8):
            locator = self.store.get(
                EVIDENCE_SHARE_LOCATOR_TENANT,
                EVIDENCE_SHARE_LOCATOR_KIND,
                share_id,
            )
            if locator is None:
                return
            try:
                self.store.delete(
                    EVIDENCE_SHARE_LOCATOR_TENANT,
                    EVIDENCE_SHARE_LOCATOR_KIND,
                    share_id,
                    expected_version=locator.version,
                )
                return
            except VersionConflict:
                continue
            except Exception as exc:
                raise EvidenceShareStorageError(
                    "Evidence share could not be disabled."
                ) from exc
        raise EvidenceShareStorageError("Evidence share disable conflicted repeatedly.")

    def _delete_locator_best_effort(self, locator: LedgerRecord) -> None:
        try:
            self.store.delete(
                locator.tenant_id,
                locator.kind,
                locator.record_id,
                expected_version=locator.version,
            )
        except Exception:
            pass

    def _mark_revoked_best_effort(
        self,
        record: LedgerRecord,
        *,
        now: datetime,
        request_id_sha256: str,
    ) -> None:
        payload = dict(record.payload)
        payload["revoked_at"] = _iso(now)
        payload["revoked_request_id_sha256"] = request_id_sha256
        payload["revoked_by_account_id"] = str(payload.get("account_id") or "") or None
        try:
            self.store.put(
                record.with_payload(payload, now=now), expected_version=record.version
            )
        except Exception:
            pass


def _request_id_sha256(request_id: str | None) -> str:
    value = (request_id or "").encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _required_identity(value: str, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _validate_share_id(share_id: str) -> None:
    if not isinstance(share_id, str) or not _SHARE_ID_PATTERN.fullmatch(share_id):
        raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")


def _utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value, "timestamp").isoformat().replace("+00:00", "Z")


def _parse_payload_datetime(payload: Mapping[str, object], field: str) -> datetime:
    value = payload.get(field)
    if not isinstance(value, str):
        raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _utc(parsed, field).replace(microsecond=0)
    except (TypeError, ValueError) as exc:
        raise EvidenceShareUnavailable(
            "Shared Evidence Packet is unavailable."
        ) from exc


def _parse_optional_payload_datetime(
    payload: Mapping[str, object], field: str
) -> datetime | None:
    if payload.get(field) is None:
        return None
    return _parse_payload_datetime(payload, field)


def _payload_text(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
    return value.strip()


def _payload_sha256(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise EvidenceShareUnavailable("Shared Evidence Packet is unavailable.")
    return value


__all__ = [
    "CreatedEvidenceShare",
    "EVIDENCE_SHARE_EVENT_KIND",
    "EVIDENCE_SHARE_KIND",
    "EVIDENCE_SHARE_LOCATOR_KIND",
    "EVIDENCE_SHARE_LOCATOR_TENANT",
    "EvidenceShare",
    "EvidenceShareConfigurationError",
    "EvidenceShareError",
    "EvidenceShareNotFound",
    "EvidenceShareService",
    "EvidenceShareStorageError",
    "EvidenceShareUnavailable",
    "MAX_SHARE_LIFETIME",
]
