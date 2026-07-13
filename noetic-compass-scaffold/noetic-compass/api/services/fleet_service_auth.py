"""Durable tenant-bound authentication for CAS Harness fleet service callbacks.

Customer JWTs authorize people at the control plane.  They are intentionally not valid worker,
merger, or verifier credentials.  This module issues a separate random service credential, stores
only a pepper-keyed digest, scopes it to one tenant/audit/fleet (and usually one worker), and
requires a fresh timestamp plus a durable one-time nonce on every callback.

The feature is dark unless ``NC_FLEET_SERVICE_AUTH_ENABLED=true``.  Its caller must supply the
shared account-mode ``StateStore``; there is no in-memory fallback.  Therefore credential expiry,
revocation, and consumed nonces survive a process restart and are shared by Postgres replicas.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import re
import secrets
from typing import Iterable, Literal, Mapping
import uuid

from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    StateStoreError,
    VersionConflict,
)


FleetServiceCapability = Literal[
    "register_worker",
    "heartbeat",
    "mark_running",
    "submit_evidence",
    "lease_job",
    "submit_receipt",
    "merge_distributed",
    "merge_fleet",
    "verify_fleet",
]

CAPABILITIES: frozenset[str] = frozenset(
    {
        "register_worker",
        "heartbeat",
        "mark_running",
        "submit_evidence",
        "lease_job",
        "submit_receipt",
        "merge_distributed",
        "merge_fleet",
        "verify_fleet",
    }
)
WORKER_CAPABILITIES: frozenset[str] = frozenset(
    {
        "register_worker",
        "heartbeat",
        "mark_running",
        "submit_evidence",
        "lease_job",
        "submit_receipt",
    }
)
CONTROLLER_CAPABILITIES: frozenset[str] = CAPABILITIES - WORKER_CAPABILITIES

_CREDENTIAL_KIND = "fleet_service_credential"
_AUDIT_OWNER_KIND = "fleet_service_audit_owner"
_NONCE_KIND = "fleet_service_nonce"
_TOKEN_PREFIX = "casfs_"
_CREDENTIAL_ID_RE = re.compile(r"^fsc_[0-9a-f]{32}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_SCHEMA_VERSION = "cas_fleet_service_credential.v1"
_DUMMY_DIGEST = "0" * 64


class FleetServiceAuthError(RuntimeError):
    """Base failure for service-credential persistence and policy."""


class FleetServiceAuthenticationError(FleetServiceAuthError):
    """Publicly indistinguishable invalid/expired/revoked/replayed credential."""


class FleetServiceAuthorizationError(FleetServiceAuthError):
    """A valid credential lacks the required scope or capability."""


@dataclass(frozen=True, slots=True)
class FleetServiceCredential:
    credential_id: str
    tenant_id: str
    audit_id: str
    fleet_id: str
    worker_id: str | None
    capabilities: tuple[str, ...]
    secret_digest: str
    issued_by_account_id: str
    created_at: str
    expires_at: str
    revoked_at: str | None = None
    revoked_by_account_id: str | None = None
    api_credential: str | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= _parse_time(self.expires_at)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "credential_id": self.credential_id,
            "tenant_id": self.tenant_id,
            "audit_id": self.audit_id,
            "fleet_id": self.fleet_id,
            "worker_id": self.worker_id,
            "capabilities": list(self.capabilities),
            "secret_digest": self.secret_digest,
            "issued_by_account_id": self.issued_by_account_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "revoked_by_account_id": self.revoked_by_account_id,
        }

    def to_public_dict(self, *, include_secret: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "credential_id": self.credential_id,
            "tenant_id": self.tenant_id,
            "audit_id": self.audit_id,
            "fleet_id": self.fleet_id,
            "worker_id": self.worker_id,
            "capabilities": list(self.capabilities),
            "issued_by_account_id": self.issued_by_account_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "revoked_by_account_id": self.revoked_by_account_id,
            "status": "revoked" if self.is_revoked else (
                "expired" if self.is_expired() else "active"
            ),
        }
        if include_secret:
            payload["api_credential"] = self.api_credential
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "FleetServiceCredential":
        capabilities = _validate_capabilities(payload.get("capabilities") or ())
        return cls(
            credential_id=str(payload["credential_id"]),
            tenant_id=str(payload["tenant_id"]),
            audit_id=str(payload["audit_id"]),
            fleet_id=str(payload["fleet_id"]),
            worker_id=_optional_text(payload.get("worker_id")),
            capabilities=capabilities,
            secret_digest=str(payload["secret_digest"]),
            issued_by_account_id=str(payload["issued_by_account_id"]),
            created_at=str(payload["created_at"]),
            expires_at=str(payload["expires_at"]),
            revoked_at=_optional_text(payload.get("revoked_at")),
            revoked_by_account_id=_optional_text(payload.get("revoked_by_account_id")),
        )


@dataclass(frozen=True, slots=True)
class FleetServicePrincipal:
    credential_id: str
    tenant_id: str
    audit_id: str
    fleet_id: str
    worker_id: str | None
    capabilities: tuple[str, ...]


class FleetServiceAuthStore:
    """Fleet service-auth domain over a required durable/shared ``StateStore``."""

    def __init__(self, store: StateStore, *, pepper: str, max_clock_skew_seconds: int = 300) -> None:
        if store is None:
            raise FleetServiceAuthError("Fleet service authentication requires durable storage.")
        if len((pepper or "").encode("utf-8")) < 32:
            raise FleetServiceAuthError("Fleet service credential pepper must contain at least 32 bytes.")
        if not 30 <= int(max_clock_skew_seconds) <= 900:
            raise FleetServiceAuthError("Fleet service clock skew must be between 30 and 900 seconds.")
        self._store = store
        self._pepper = pepper.encode("utf-8")
        self._clock_skew = int(max_clock_skew_seconds)

    # --- account/customer control plane ---------------------------------

    def record_audit_owner(self, *, tenant_id: str, account_id: str, audit_id: str) -> None:
        tenant = _required_text(tenant_id, "tenant_id")
        account = _required_text(account_id, "account_id")
        audit = _required_text(audit_id, "audit_id")
        record = LedgerRecord.new(
            tenant_id=tenant,
            kind=_AUDIT_OWNER_KIND,
            record_id=audit,
            payload={"tenant_id": tenant, "account_id": account, "audit_id": audit},
            parent_ids=(account,),
            source="fleet_service_auth.record_audit_owner",
            trace_id=audit,
        )
        try:
            self._store.put(record, expected_version=0)
        except VersionConflict:
            current = self._store.get(tenant, _AUDIT_OWNER_KIND, audit)
            if current is None or str(current.payload.get("account_id") or "") != account:
                raise FleetServiceAuthorizationError("Distributed audit ownership conflict.")

    def account_owns_audit(self, *, tenant_id: str, account_id: str, audit_id: str) -> bool:
        record = self._store.get(tenant_id, _AUDIT_OWNER_KIND, audit_id)
        return bool(
            record is not None
            and hmac.compare_digest(str(record.payload.get("tenant_id") or ""), tenant_id)
            and hmac.compare_digest(str(record.payload.get("account_id") or ""), account_id)
        )

    def tenant_owns_audit(self, *, tenant_id: str, audit_id: str) -> bool:
        record = self._store.get(tenant_id, _AUDIT_OWNER_KIND, audit_id)
        return bool(
            record is not None
            and hmac.compare_digest(str(record.payload.get("tenant_id") or ""), tenant_id)
        )

    def list_owned_audit_ids(self, *, tenant_id: str) -> tuple[str, ...]:
        return tuple(
            str(record.payload["audit_id"])
            for record in self._store.list(tenant_id, _AUDIT_OWNER_KIND)
            if str(record.payload.get("tenant_id") or "") == tenant_id
        )

    def issue_credential(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
        capabilities: Iterable[str],
        worker_id: str | None = None,
        ttl_seconds: int = 3600,
        now: datetime | None = None,
    ) -> FleetServiceCredential:
        tenant = _required_text(tenant_id, "tenant_id")
        account = _required_text(account_id, "account_id")
        audit = _required_text(audit_id, "audit_id")
        fleet = _required_text(fleet_id, "fleet_id")
        worker = _optional_text(worker_id)
        caps = _validate_capabilities(capabilities)
        if not self.tenant_owns_audit(tenant_id=tenant, audit_id=audit):
            raise FleetServiceAuthorizationError("Distributed audit is not owned by this tenant.")
        if fleet != audit:
            raise FleetServiceAuthorizationError("Fleet credential must be scoped to its audit fleet.")
        if not 60 <= int(ttl_seconds) <= 86_400:
            raise FleetServiceAuthError("Service credential ttl_seconds must be between 60 and 86400.")
        if set(caps) & WORKER_CAPABILITIES and not worker:
            raise FleetServiceAuthError("Worker capabilities require worker_id scope.")
        if worker and set(caps) & CONTROLLER_CAPABILITIES:
            raise FleetServiceAuthError("Worker-scoped credentials cannot receive controller capabilities.")

        stamp = now or datetime.now(UTC)
        credential_id = f"fsc_{uuid.uuid4().hex}"
        raw = f"{_TOKEN_PREFIX}{credential_id}.{secrets.token_urlsafe(32)}"
        credential = FleetServiceCredential(
            credential_id=credential_id,
            tenant_id=tenant,
            audit_id=audit,
            fleet_id=fleet,
            worker_id=worker,
            capabilities=caps,
            secret_digest=self._digest(raw),
            issued_by_account_id=account,
            created_at=stamp.isoformat(),
            expires_at=(stamp + timedelta(seconds=int(ttl_seconds))).isoformat(),
            api_credential=raw,
        )
        record = LedgerRecord.new(
            tenant_id=tenant,
            kind=_CREDENTIAL_KIND,
            record_id=credential_id,
            payload=credential.to_payload(),
            parent_ids=(account, audit),
            source="fleet_service_auth.issue",
            trace_id=audit,
        )
        self._store.put(record, expected_version=0)
        return credential

    def list_credentials(self, *, tenant_id: str, audit_id: str) -> tuple[FleetServiceCredential, ...]:
        return tuple(
            credential
            for record in self._store.list(tenant_id, _CREDENTIAL_KIND)
            if (credential := FleetServiceCredential.from_payload(record.payload)).audit_id == audit_id
        )

    def revoke_credential(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        credential_id: str,
        now: datetime | None = None,
    ) -> FleetServiceCredential | None:
        actor = _required_text(account_id, "account_id")
        if not self.tenant_owns_audit(tenant_id=tenant_id, audit_id=audit_id):
            raise FleetServiceAuthorizationError("Distributed audit is not owned by this tenant.")
        for _ in range(12):
            record = self._store.get(tenant_id, _CREDENTIAL_KIND, credential_id)
            if record is None:
                return None
            current = FleetServiceCredential.from_payload(record.payload)
            if current.audit_id != audit_id:
                return None
            if current.revoked_at is not None:
                return current
            updated = replace(
                current,
                revoked_at=(now or datetime.now(UTC)).isoformat(),
                revoked_by_account_id=actor,
            )
            try:
                self._store.put(
                    record.with_payload(updated.to_payload()), expected_version=record.version
                )
                return updated
            except VersionConflict:
                continue
        raise FleetServiceAuthError("Credential revocation contention did not converge.")

    # --- service callback authentication --------------------------------

    def authenticate(
        self,
        *,
        tenant_id: str,
        api_credential: str,
        timestamp: str,
        nonce: str,
        required_capability: str,
        audit_id: str,
        fleet_id: str,
        worker_id: str | None = None,
        now: datetime | None = None,
    ) -> FleetServicePrincipal:
        stamp = now or datetime.now(UTC)
        tenant = _required_text(tenant_id, "tenant_id")
        token = (api_credential or "").strip()
        credential_id = _credential_id_from_token(token)
        record = (
            self._store.get(tenant, _CREDENTIAL_KIND, credential_id)
            if credential_id is not None
            else None
        )
        credential = (
            FleetServiceCredential.from_payload(record.payload) if record is not None else None
        )
        expected = credential.secret_digest if credential is not None else _DUMMY_DIGEST
        digest_ok = hmac.compare_digest(expected, self._digest(token))
        if credential is None or not digest_ok:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        if credential.is_revoked or credential.is_expired(now=stamp):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        if not _timestamp_is_fresh(timestamp, now=stamp, skew_seconds=self._clock_skew):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        if not _NONCE_RE.fullmatch(nonce or ""):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        if not self.tenant_owns_audit(tenant_id=tenant, audit_id=audit_id):
            raise FleetServiceAuthorizationError("Fleet service scope denied.")
        if (
            credential.tenant_id != tenant
            or credential.audit_id != audit_id
            or credential.fleet_id != fleet_id
            or required_capability not in credential.capabilities
        ):
            raise FleetServiceAuthorizationError("Fleet service scope denied.")
        expected_worker = credential.worker_id
        requested_worker = _optional_text(worker_id)
        if expected_worker is not None and expected_worker != requested_worker:
            raise FleetServiceAuthorizationError("Fleet service scope denied.")
        if required_capability in WORKER_CAPABILITIES and expected_worker is None:
            raise FleetServiceAuthorizationError("Fleet service scope denied.")

        # Consume only after every credential/scope check. expected_version=0 is the durable,
        # cross-process compare-and-set: simultaneous copies of one callback have one winner.
        nonce_id = "fsn_" + hashlib.sha256(
            f"{credential.credential_id}:{nonce}".encode("utf-8")
        ).hexdigest()
        nonce_record = LedgerRecord.new(
            tenant_id=tenant,
            kind=_NONCE_KIND,
            record_id=nonce_id,
            payload={
                "credential_id": credential.credential_id,
                "nonce_sha256": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
                "consumed_at": stamp.isoformat(),
                "expires_at": (stamp + timedelta(seconds=self._clock_skew * 2)).isoformat(),
            },
            parent_ids=(credential.credential_id, audit_id),
            source="fleet_service_auth.authenticate",
            trace_id=audit_id,
        )
        try:
            self._store.put(nonce_record, expected_version=0)
        except VersionConflict as exc:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.") from exc
        except StateStoreError as exc:
            raise FleetServiceAuthenticationError("Fleet service verification unavailable.") from exc

        return FleetServicePrincipal(
            credential_id=credential.credential_id,
            tenant_id=credential.tenant_id,
            audit_id=credential.audit_id,
            fleet_id=credential.fleet_id,
            worker_id=credential.worker_id,
            capabilities=credential.capabilities,
        )

    def _digest(self, value: str) -> str:
        return hmac.new(self._pepper, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _credential_id_from_token(token: str) -> str | None:
    if not token.startswith(_TOKEN_PREFIX) or "." not in token:
        return None
    head, secret = token[len(_TOKEN_PREFIX) :].split(".", 1)
    if not _CREDENTIAL_ID_RE.fullmatch(head) or len(secret) < 32:
        return None
    return head


def _validate_capabilities(values: Iterable[object]) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
    if not result:
        raise FleetServiceAuthError("At least one fleet service capability is required.")
    unknown = set(result) - CAPABILITIES
    if unknown:
        raise FleetServiceAuthError(
            "Unknown fleet service capabilities: " + ", ".join(sorted(unknown))
        )
    return tuple(sorted(result))


def _timestamp_is_fresh(raw: str, *, now: datetime, skew_seconds: int) -> bool:
    try:
        supplied = datetime.fromtimestamp(int(raw), tz=UTC)
    except (TypeError, ValueError, OverflowError):
        return False
    return abs((now - supplied).total_seconds()) <= skew_seconds


def _parse_time(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _required_text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise FleetServiceAuthError(f"{field} is required.")
    return text


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
