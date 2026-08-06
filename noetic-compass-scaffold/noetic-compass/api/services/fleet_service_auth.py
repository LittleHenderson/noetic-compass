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
_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
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
    account_id: str
    audit_id: str
    fleet_id: str
    worker_id: str | None
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FleetServiceNonceReceipt:
    """Server-side structural receipt for one durably consumed callback nonce.

    This is not a signature, trusted timestamp, worker attestation, run-nonce
    issuance receipt, or proof that callback payload bytes are authoritative.
    It exposes only the exact durable nonce record needed by research adapters
    to bind an already-authenticated callback to another strict envelope.
    """

    nonce_id: str
    credential_id: str
    tenant_id: str
    account_id: str
    audit_id: str
    fleet_id: str
    worker_id: str | None
    capabilities: tuple[str, ...]
    nonce_sha256: str
    byte_length: int
    consumed_at: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class FleetServiceAuthenticatedCallback:
    """Principal plus the exact nonce record created by authentication."""

    principal: FleetServicePrincipal
    nonce_receipt: FleetServiceNonceReceipt


@dataclass(frozen=True, slots=True)
class FleetServiceIntakeBinding:
    """Exact request identity atomically attached to one callback nonce.

    This is a server-observed HTTP intake record.  It authenticates neither
    the carrier's author nor the model execution and provides no trusted time.
    """

    http_method: str
    route_path: str
    job_id: str
    run_id: str
    authorization_sha256: str | None
    carrier_sha256: str
    carrier_byte_length: int
    lease_token_sha256: str | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]{3,12}", self.http_method or ""):
            raise FleetServiceAuthError("Invalid bound-intake HTTP method.")
        if (
            not isinstance(self.route_path, str)
            or not self.route_path.startswith("/")
            or "?" in self.route_path
            or "#" in self.route_path
            or any(character.isspace() for character in self.route_path)
            or len(self.route_path.encode("utf-8")) > 2048
        ):
            raise FleetServiceAuthError("Invalid bound-intake route path.")
        _required_text(self.job_id, "job_id")
        _required_text(self.run_id, "run_id")
        if self.authorization_sha256 is not None and not _UPPER_SHA256_RE.fullmatch(
            self.authorization_sha256
        ):
            raise FleetServiceAuthError(
                "Bound-intake authorization_sha256 must be uppercase SHA-256."
            )
        if self.lease_token_sha256 is not None and not _UPPER_SHA256_RE.fullmatch(
            self.lease_token_sha256
        ):
            raise FleetServiceAuthError(
                "Bound-intake lease_token_sha256 must be uppercase SHA-256."
            )
        if not _UPPER_SHA256_RE.fullmatch(self.carrier_sha256 or ""):
            raise FleetServiceAuthError(
                "Bound-intake carrier_sha256 must be uppercase SHA-256."
            )
        if (
            type(self.carrier_byte_length) is not int
            or self.carrier_byte_length < 0
            or self.carrier_byte_length > 2_000_000
        ):
            raise FleetServiceAuthError("Invalid bound-intake carrier byte length.")

    def to_payload(self) -> dict[str, object]:
        return {
            "http_method": self.http_method,
            "route_path": self.route_path,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "authorization_sha256": self.authorization_sha256,
            "lease_token_sha256": self.lease_token_sha256,
            "carrier_sha256": self.carrier_sha256,
            "carrier_byte_length": self.carrier_byte_length,
            "assurance": {
                "scope": "SERVER_OBSERVED_HTTP_INTAKE_ONLY",
                "payload_authentication": "NOT_ESTABLISHED",
                "execution_authentication": "NOT_ESTABLISHED",
                "trusted_time": "NOT_ESTABLISHED",
            },
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "FleetServiceIntakeBinding":
        required_keys = {
            "http_method",
            "route_path",
            "job_id",
            "run_id",
            "authorization_sha256",
            "carrier_sha256",
            "carrier_byte_length",
            "assurance",
        }
        payload_keys = set(payload)
        if not required_keys.issubset(payload_keys) or not payload_keys.issubset(
            required_keys | {"lease_token_sha256"}
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        assurance = payload.get("assurance")
        if assurance != {
            "scope": "SERVER_OBSERVED_HTTP_INTAKE_ONLY",
            "payload_authentication": "NOT_ESTABLISHED",
            "execution_authentication": "NOT_ESTABLISHED",
            "trusted_time": "NOT_ESTABLISHED",
        }:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        length = payload.get("carrier_byte_length")
        if type(length) is not int:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        authorization_sha256 = payload.get("authorization_sha256")
        if authorization_sha256 is not None and not isinstance(
            authorization_sha256, str
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        lease_token_sha256 = payload.get("lease_token_sha256")
        if lease_token_sha256 is not None and not isinstance(
            lease_token_sha256, str
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        try:
            return cls(
                http_method=str(payload["http_method"]),
                route_path=str(payload["route_path"]),
                job_id=str(payload["job_id"]),
                run_id=str(payload["run_id"]),
                authorization_sha256=authorization_sha256,
                lease_token_sha256=lease_token_sha256,
                carrier_sha256=str(payload["carrier_sha256"]),
                carrier_byte_length=length,
            )
        except (KeyError, FleetServiceAuthError) as exc:
            raise FleetServiceAuthenticationError(
                "Invalid fleet service credential."
            ) from exc


@dataclass(frozen=True, slots=True)
class FleetServiceBoundIntakeReceipt:
    """Authenticated callback plus its same-row exact HTTP intake binding."""

    callback: FleetServiceAuthenticatedCallback
    intake_binding: FleetServiceIntakeBinding


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

    def audit_owner_account_id(self, *, tenant_id: str, audit_id: str) -> str | None:
        """Return the immutable creator account for tenant-scoped packet provenance."""
        record = self._store.get(tenant_id, _AUDIT_OWNER_KIND, audit_id)
        if (
            record is None
            or not hmac.compare_digest(
                str(record.payload.get("tenant_id") or ""), tenant_id
            )
            or not hmac.compare_digest(
                str(record.payload.get("audit_id") or ""), audit_id
            )
        ):
            return None
        account_id = str(record.payload.get("account_id") or "").strip()
        return account_id or None

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
        _intake_binding: FleetServiceIntakeBinding | None = None,
    ) -> FleetServicePrincipal:
        if _intake_binding is not None and type(_intake_binding) is not FleetServiceIntakeBinding:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
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
        owner_account_id = self.audit_owner_account_id(
            tenant_id=tenant, audit_id=audit_id
        )
        if owner_account_id is None:
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
        nonce_payload: dict[str, object] = {
            "schema_version": (
                "cas_fleet_service_bound_intake_receipt.v2"
                if _intake_binding is not None
                else "cas_fleet_service_nonce_receipt.v1"
            ),
            "nonce_id": nonce_id,
            "credential_id": credential.credential_id,
            "tenant_id": credential.tenant_id,
            "account_id": owner_account_id,
            "audit_id": credential.audit_id,
            "fleet_id": credential.fleet_id,
            "worker_id": credential.worker_id,
            "capabilities": list(credential.capabilities),
            "nonce_sha256": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            "byte_length": len(nonce.encode("utf-8")),
            "consumed_at": stamp.isoformat(),
            "expires_at": (stamp + timedelta(seconds=self._clock_skew * 2)).isoformat(),
        }
        if _intake_binding is not None:
            nonce_payload["intake_binding"] = _intake_binding.to_payload()
        nonce_record = LedgerRecord.new(
            tenant_id=tenant,
            kind=_NONCE_KIND,
            record_id=nonce_id,
            payload=nonce_payload,
            parent_ids=(credential.credential_id, audit_id),
            source=(
                "fleet_service_auth.authenticate_bound_intake"
                if _intake_binding is not None
                else "fleet_service_auth.authenticate"
            ),
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
            account_id=owner_account_id,
            audit_id=credential.audit_id,
            fleet_id=credential.fleet_id,
            worker_id=credential.worker_id,
            capabilities=credential.capabilities,
        )

    def authenticate_with_nonce_receipt(
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
    ) -> FleetServiceAuthenticatedCallback:
        """Authenticate once and return the exact durable nonce record.

        ``authenticate`` remains the compatibility surface used by existing
        routes.  This additive method is for dark research adapters that must
        compare a strict worker envelope with the server-created nonce record.
        It does not make the callback timestamp trusted or attest execution.
        """

        principal = self.authenticate(
            tenant_id=tenant_id,
            api_credential=api_credential,
            timestamp=timestamp,
            nonce=nonce,
            required_capability=required_capability,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
            now=now,
        )
        receipt = self.consumed_nonce_receipt(principal=principal, nonce=nonce)
        return FleetServiceAuthenticatedCallback(
            principal=principal,
            nonce_receipt=receipt,
        )

    def authenticate_with_bound_intake_receipt(
        self,
        *,
        tenant_id: str,
        api_credential: str,
        timestamp: str,
        nonce: str,
        required_capability: str,
        audit_id: str,
        fleet_id: str,
        intake_binding: FleetServiceIntakeBinding,
        worker_id: str | None = None,
        now: datetime | None = None,
    ) -> FleetServiceBoundIntakeReceipt:
        """Consume one callback nonce and its exact intake binding atomically."""

        if type(intake_binding) is not FleetServiceIntakeBinding:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        principal = self.authenticate(
            tenant_id=tenant_id,
            api_credential=api_credential,
            timestamp=timestamp,
            nonce=nonce,
            required_capability=required_capability,
            audit_id=audit_id,
            fleet_id=fleet_id,
            worker_id=worker_id,
            now=now,
            _intake_binding=intake_binding,
        )
        callback = FleetServiceAuthenticatedCallback(
            principal=principal,
            nonce_receipt=self.consumed_nonce_receipt(
                principal=principal,
                nonce=nonce,
            ),
        )
        receipt = FleetServiceBoundIntakeReceipt(
            callback=callback,
            intake_binding=intake_binding,
        )
        return self.verify_bound_intake_receipt(receipt)

    def consumed_nonce_receipt(
        self,
        *,
        principal: FleetServicePrincipal,
        nonce: str,
    ) -> FleetServiceNonceReceipt:
        """Re-read and validate a nonce consumed for ``principal``.

        The raw nonce is never returned or stored.  A missing, legacy,
        cross-principal, or internally inconsistent record fails closed.
        """

        if not _NONCE_RE.fullmatch(nonce or ""):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        raw = nonce.encode("utf-8")
        nonce_id = "fsn_" + hashlib.sha256(
            f"{principal.credential_id}:{nonce}".encode("utf-8")
        ).hexdigest()
        try:
            record = self._store.get(principal.tenant_id, _NONCE_KIND, nonce_id)
        except StateStoreError as exc:
            raise FleetServiceAuthenticationError(
                "Fleet service verification unavailable."
            ) from exc
        if record is None:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        payload = record.payload
        expected_digest = hashlib.sha256(raw).hexdigest()
        byte_length = payload.get("byte_length")
        schema_version = payload.get("schema_version")
        source = record.source
        schema_source_ok = (
            schema_version == "cas_fleet_service_nonce_receipt.v1"
            and source == "fleet_service_auth.authenticate"
            and "intake_binding" not in payload
        ) or (
            schema_version == "cas_fleet_service_bound_intake_receipt.v2"
            and source == "fleet_service_auth.authenticate_bound_intake"
            and isinstance(payload.get("intake_binding"), Mapping)
        )
        if (
            not schema_source_ok
            or payload.get("nonce_id") != nonce_id
            or payload.get("credential_id") != principal.credential_id
            or payload.get("tenant_id") != principal.tenant_id
            or payload.get("account_id") != principal.account_id
            or payload.get("audit_id") != principal.audit_id
            or payload.get("fleet_id") != principal.fleet_id
            or payload.get("worker_id") != principal.worker_id
            or payload.get("capabilities") != list(principal.capabilities)
            or not isinstance(payload.get("nonce_sha256"), str)
            or not hmac.compare_digest(str(payload["nonce_sha256"]), expected_digest)
            or not isinstance(byte_length, int)
            or isinstance(byte_length, bool)
            or byte_length != len(raw)
            or record.version != 1
            or record.parent_ids != (principal.credential_id, principal.audit_id)
            or record.trace_id != principal.audit_id
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        consumed_at = _optional_text(payload.get("consumed_at"))
        expires_at = _optional_text(payload.get("expires_at"))
        if consumed_at is None or expires_at is None:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        try:
            consumed_time = _parse_time(consumed_at)
            expires_time = _parse_time(expires_at)
        except ValueError as exc:
            raise FleetServiceAuthenticationError(
                "Invalid fleet service credential."
            ) from exc
        if expires_time <= consumed_time:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        return FleetServiceNonceReceipt(
            nonce_id=nonce_id,
            credential_id=principal.credential_id,
            tenant_id=principal.tenant_id,
            account_id=principal.account_id,
            audit_id=principal.audit_id,
            fleet_id=principal.fleet_id,
            worker_id=principal.worker_id,
            capabilities=principal.capabilities,
            # Harness-v2 strict artifacts use the repository-wide uppercase
            # SHA-256 representation.  The durable record remains the exact
            # lowercase digest historically used by this service.
            nonce_sha256=expected_digest.upper(),
            byte_length=byte_length,
            consumed_at=consumed_at,
            expires_at=expires_at,
        )

    def verify_authenticated_callback(
        self,
        callback: FleetServiceAuthenticatedCallback,
    ) -> FleetServiceAuthenticatedCallback:
        """Re-read a callback carrier against the exact durable nonce row.

        This supports a downstream acceptance adapter without exposing the raw
        transport nonce.  It proves only that this server ledger contains the
        one-use record and exact principal scope; it is not a signature, trusted
        clock, worker attestation, or payload authentication claim.
        """

        if type(callback) is not FleetServiceAuthenticatedCallback:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        principal = callback.principal
        receipt = callback.nonce_receipt
        if (
            type(principal) is not FleetServicePrincipal
            or type(receipt) is not FleetServiceNonceReceipt
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        expected_scope = (
            principal.credential_id,
            principal.tenant_id,
            principal.account_id,
            principal.audit_id,
            principal.fleet_id,
            principal.worker_id,
            principal.capabilities,
        )
        receipt_scope = (
            receipt.credential_id,
            receipt.tenant_id,
            receipt.account_id,
            receipt.audit_id,
            receipt.fleet_id,
            receipt.worker_id,
            receipt.capabilities,
        )
        if receipt_scope != expected_scope:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        try:
            record = self._store.get(receipt.tenant_id, _NONCE_KIND, receipt.nonce_id)
        except StateStoreError as exc:
            raise FleetServiceAuthenticationError(
                "Fleet service verification unavailable."
            ) from exc
        if record is None:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        payload = record.payload
        schema_version = payload.get("schema_version")
        source = record.source
        schema_source_ok = (
            schema_version == "cas_fleet_service_nonce_receipt.v1"
            and source == "fleet_service_auth.authenticate"
            and "intake_binding" not in payload
        ) or (
            schema_version == "cas_fleet_service_bound_intake_receipt.v2"
            and source == "fleet_service_auth.authenticate_bound_intake"
            and isinstance(payload.get("intake_binding"), Mapping)
        )
        if (
            not schema_source_ok
            or payload.get("nonce_id") != receipt.nonce_id
            or payload.get("credential_id") != receipt.credential_id
            or payload.get("tenant_id") != receipt.tenant_id
            or payload.get("account_id") != receipt.account_id
            or payload.get("audit_id") != receipt.audit_id
            or payload.get("fleet_id") != receipt.fleet_id
            or payload.get("worker_id") != receipt.worker_id
            or payload.get("capabilities") != list(receipt.capabilities)
            or str(payload.get("nonce_sha256") or "").upper() != receipt.nonce_sha256
            or payload.get("byte_length") != receipt.byte_length
            or payload.get("consumed_at") != receipt.consumed_at
            or payload.get("expires_at") != receipt.expires_at
            or record.version != 1
            or record.parent_ids != (receipt.credential_id, receipt.audit_id)
            or record.trace_id != receipt.audit_id
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        try:
            consumed_time = _parse_time(receipt.consumed_at)
            expires_time = _parse_time(receipt.expires_at)
        except ValueError as exc:
            raise FleetServiceAuthenticationError(
                "Invalid fleet service credential."
            ) from exc
        if expires_time <= consumed_time:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        return callback

    def verify_bound_intake_receipt(
        self,
        receipt: FleetServiceBoundIntakeReceipt,
    ) -> FleetServiceBoundIntakeReceipt:
        """Re-read the exact v2 nonce row and compare its request binding."""

        if type(receipt) is not FleetServiceBoundIntakeReceipt:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        callback = self.verify_authenticated_callback(receipt.callback)
        nonce_receipt = callback.nonce_receipt
        try:
            record = self._store.get(
                nonce_receipt.tenant_id, _NONCE_KIND, nonce_receipt.nonce_id
            )
        except StateStoreError as exc:
            raise FleetServiceAuthenticationError(
                "Fleet service verification unavailable."
            ) from exc
        if (
            record is None
            or record.payload.get("schema_version")
            != "cas_fleet_service_bound_intake_receipt.v2"
            or record.source != "fleet_service_auth.authenticate_bound_intake"
            or not isinstance(record.payload.get("intake_binding"), Mapping)
        ):
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        loaded = FleetServiceIntakeBinding.from_payload(
            record.payload["intake_binding"]  # type: ignore[arg-type]
        )
        if loaded != receipt.intake_binding:
            raise FleetServiceAuthenticationError("Invalid fleet service credential.")
        return receipt

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
