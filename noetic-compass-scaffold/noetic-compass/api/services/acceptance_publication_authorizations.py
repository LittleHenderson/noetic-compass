"""Short-lived, content-addressed owner authorization for authority publication.

This plane records only an authenticated primary-tenant owner's authorization
to perform one exactly bound ``publish`` operation.  It does not record or
create legal approval, claim approval, gate evidence, or a release decision.

Records are immutable StateStore rows written with ``expected_version=0`` and
addressed by the SHA-256 of their strict canonical JSON bytes.  There is no
head, list, update, or delete operation.  Expiry is enforced on every read; the
underlying audit row may remain after expiry, but can no longer authorize a
publication.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import re
from typing import Any

from api.acceptance_authority_contract import (
    ACCEPTANCE_AUTHORITY_PATH_BY_GATE,
    PRODUCTION_API_ORIGIN,
    acceptance_publication_authorization_url,
)
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)
from api.services.customer_production_pseudonyms import (
    CustomerProductionPseudonymizer,
    PUBLICATION_ACCOUNT_DOMAIN,
    PUBLICATION_CONTENT_BINDING_DOMAIN,
    PUBLICATION_TENANT_DOMAIN,
    validate_public_pseudonym_metadata,
    validate_public_pseudonym_subject,
)


SCHEMA_VERSION = "cas_harness_acceptance_publication_authorization.v2"
IDENTITY_BINDING_SCHEMA_VERSION = (
    "cas_harness_acceptance_publication_authorization_identity_binding.v1"
)
RECORD_TYPE = "authority_operation"
ACTION = "AUTHORIZE"
OPERATION = "publish"
REASON = "authorized_publication"
ENVIRONMENT = "public-production"
REPOSITORY = "LittleHenderson/noetic-compass"
AUTHORIZATION_TENANT_ID = "cas-harness-customer-production-authorizations"
AUTHORIZATION_KIND = "customer_production_acceptance_publication_authorization"
IDENTITY_BINDING_KIND = (
    "customer_production_acceptance_publication_authorization_identity_binding"
)
AUTHORIZATION_TTL_SECONDS = 15 * 60

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
_TENANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_ACCOUNT_ID_RE = re.compile(r"^acct-[0-9a-f]{32}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_URI_RE = re.compile(
    re.escape(f"{PRODUCTION_API_ORIGIN}/internal/acceptance-authorizations/")
    + r"(?P<authorization_sha256>[0-9a-f]{64})"
)
_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "action",
        "operation",
        "gate",
        "environment",
        "repository",
        "master_head_sha",
        "deploy_id",
        "evidence_sha256",
        "expected_head_version",
        "expected_previous_evidence_sha256",
        "reason",
        "authorized_at_utc",
        "expires_at_utc",
        "authorized_by",
    }
)
_ACTOR_KEYS = frozenset(
    {
        "pseudonymization_scheme",
        "pseudonym_key_id",
        "tenant_subject",
        "account_subject",
        "role",
    }
)
_IDENTITY_BINDING_KEYS = frozenset(
    {
        "schema_version",
        "authorization_sha256",
        "actor_tenant_id",
        "actor_account_id",
        "pseudonym_key_id",
        "content_binding_hmac",
    }
)


class AcceptancePublicationAuthorizationError(RuntimeError):
    """Base class for publication-authorization failures."""


class AcceptancePublicationAuthorizationInvalid(
    AcceptancePublicationAuthorizationError
):
    """The requested authorization or binding is malformed or inapplicable."""


class AcceptancePublicationAuthorizationNotFound(
    AcceptancePublicationAuthorizationError
):
    """The content-addressed record is absent or no longer live."""


class AcceptancePublicationAuthorizationUnavailable(
    AcceptancePublicationAuthorizationError
):
    """The durable record is unavailable or failed integrity validation."""


@dataclass(frozen=True, slots=True)
class AcceptancePublicationAuthorization:
    sha256: str
    uri: str
    body: bytes
    payload: Mapping[str, Any]
    expires_at: datetime


class AcceptancePublicationAuthorizationStore:
    """Create-only authorization records over one shared StateStore."""

    def __init__(
        self,
        store: StateStore,
        *,
        primary_tenant_id: str,
        pseudonymizer: CustomerProductionPseudonymizer,
    ) -> None:
        if (
            not isinstance(primary_tenant_id, str)
            or _TENANT_ID_RE.fullmatch(primary_tenant_id) is None
        ):
            raise ValueError("primary_tenant_id is invalid")
        if not isinstance(pseudonymizer, CustomerProductionPseudonymizer):
            raise ValueError("customer-production pseudonymizer is required")
        self._store = store
        self._primary_tenant_id = primary_tenant_id
        self._pseudonymizer = pseudonymizer

    def create(
        self,
        *,
        actor_tenant_id: str,
        actor_account_id: str,
        actor_role: str,
        gate: str,
        master_head_sha: str,
        deploy_id: str,
        evidence_sha256: str,
        expected_head_version: int,
        expected_previous_evidence_sha256: str | None,
        reason: str,
        now: datetime | None = None,
    ) -> AcceptancePublicationAuthorization:
        """Create exactly one fixed-TTL record from server-derived actor fields."""

        if (
            actor_role != "owner"
            or actor_tenant_id != self._primary_tenant_id
            or not isinstance(actor_account_id, str)
            or _ACCOUNT_ID_RE.fullmatch(actor_account_id) is None
        ):
            raise AcceptancePublicationAuthorizationInvalid(
                "a primary-tenant owner identity is required"
            )
        _validate_bindings(
            gate=gate,
            master_head_sha=master_head_sha,
            deploy_id=deploy_id,
            evidence_sha256=evidence_sha256,
            expected_head_version=expected_head_version,
            expected_previous_evidence_sha256=(
                expected_previous_evidence_sha256
            ),
            reason=reason,
        )
        stamp = _utc_now(now)
        expires = stamp + timedelta(seconds=AUTHORIZATION_TTL_SECONDS)
        key_id = self._pseudonymizer.active_key_id
        pseudonym_metadata = self._pseudonymizer.metadata(key_id=key_id)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "action": ACTION,
            "operation": OPERATION,
            "gate": gate,
            "environment": ENVIRONMENT,
            "repository": REPOSITORY,
            "master_head_sha": master_head_sha,
            "deploy_id": deploy_id,
            "evidence_sha256": evidence_sha256,
            "expected_head_version": expected_head_version,
            "expected_previous_evidence_sha256": (
                expected_previous_evidence_sha256
            ),
            "reason": reason,
            "authorized_at_utc": _format_utc(stamp),
            "expires_at_utc": _format_utc(expires),
            "authorized_by": {
                **pseudonym_metadata,
                "tenant_subject": self._pseudonymizer.subject(
                    domain=PUBLICATION_TENANT_DOMAIN,
                    tenant_scope=actor_tenant_id,
                    value=actor_tenant_id,
                    key_id=key_id,
                ),
                "account_subject": self._pseudonymizer.subject(
                    domain=PUBLICATION_ACCOUNT_DOMAIN,
                    tenant_scope=actor_tenant_id,
                    value=actor_account_id,
                    key_id=key_id,
                ),
                "role": actor_role,
            },
        }
        canonical = _canonical_json_bytes(payload)
        digest = hashlib.sha256(canonical).hexdigest()
        content_binding_hmac = _private_content_binding_hmac(
            self._pseudonymizer,
            authorization_sha256=digest,
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
            pseudonym_key_id=key_id,
        )
        record = LedgerRecord.new(
            tenant_id=AUTHORIZATION_TENANT_ID,
            kind=AUTHORIZATION_KIND,
            record_id=_record_id(digest),
            payload=payload,
            source="acceptance_publication_authorization",
            trace_id=digest,
            now=stamp,
        )
        identity_payload = {
            "schema_version": IDENTITY_BINDING_SCHEMA_VERSION,
            "authorization_sha256": digest,
            "actor_tenant_id": actor_tenant_id,
            "actor_account_id": actor_account_id,
            "pseudonym_key_id": key_id,
            "content_binding_hmac": content_binding_hmac,
        }
        identity = LedgerRecord.new(
            tenant_id=AUTHORIZATION_TENANT_ID,
            kind=IDENTITY_BINDING_KIND,
            record_id=_identity_binding_record_id(digest),
            payload=identity_payload,
            parent_ids=(record.record_id,),
            source="acceptance_publication_authorization",
            trace_id=digest,
            now=stamp,
        )
        try:
            stored = self._store.put(record, expected_version=0)
        except VersionConflict:
            # Recover a crash between the immutable public row and its private
            # identity binding.  Exact bytes may proceed to binding creation;
            # a conflicting row never becomes live.
            try:
                existing = self._store.get(
                    AUTHORIZATION_TENANT_ID, AUTHORIZATION_KIND, _record_id(digest)
                )
            except Exception as exc:
                raise AcceptancePublicationAuthorizationUnavailable(
                    "publication authorization store is unavailable"
                ) from exc
            if (
                existing is None
                or existing.version != 1
                or existing.source != "acceptance_publication_authorization"
                or existing.trace_id != digest
                or existing.parent_ids
                or _canonical_json_bytes(existing.payload) != canonical
            ):
                raise AcceptancePublicationAuthorizationUnavailable(
                    "content-addressed publication authorization conflicted"
                )
            stored = existing
        except Exception as exc:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization persistence failed"
            ) from exc
        if stored.version != 1:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization version is invalid"
            )
        try:
            stored_identity = self._store.put(identity, expected_version=0)
        except VersionConflict:
            try:
                stored_identity = self._store.get(
                    AUTHORIZATION_TENANT_ID,
                    IDENTITY_BINDING_KIND,
                    _identity_binding_record_id(digest),
                )
            except Exception as exc:
                raise AcceptancePublicationAuthorizationUnavailable(
                    "publication authorization identity binding is unavailable"
                ) from exc
            _validate_identity_binding_record(
                stored_identity,
                expected_digest=digest,
                content_record_id=record.record_id,
                expected_payload=identity_payload,
            )
        except Exception as exc:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization identity binding persistence failed"
            ) from exc
        if stored_identity is None or stored_identity.version != 1:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization identity binding version is invalid"
            )
        return self._decode_record(
            stored,
            stored_identity,
            expected_digest=digest,
            now=stamp,
        )

    def load(
        self, authorization_sha256: str, *, now: datetime | None = None
    ) -> AcceptancePublicationAuthorization:
        """Load one exact live record by digest; expired records act absent."""

        if (
            not isinstance(authorization_sha256, str)
            or _SHA256_RE.fullmatch(authorization_sha256) is None
        ):
            raise AcceptancePublicationAuthorizationInvalid(
                "publication authorization digest is invalid"
            )
        try:
            record = self._store.get(
                AUTHORIZATION_TENANT_ID,
                AUTHORIZATION_KIND,
                _record_id(authorization_sha256),
            )
            identity = self._store.get(
                AUTHORIZATION_TENANT_ID,
                IDENTITY_BINDING_KIND,
                _identity_binding_record_id(authorization_sha256),
            )
        except Exception as exc:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization store is unavailable"
            ) from exc
        if record is None:
            raise AcceptancePublicationAuthorizationNotFound(
                "publication authorization is unavailable"
            )
        if identity is None:
            # v1 rows deliberately cannot be promoted after the keyed schema
            # migration. A new owner authorization is required.
            raise AcceptancePublicationAuthorizationUnavailable(
                "keyed publication authorization identity binding is unavailable"
            )
        return self._decode_record(
            record,
            identity,
            expected_digest=authorization_sha256,
            now=_utc_now(now),
        )

    def assert_matches(
        self,
        *,
        authorization_artifact_uri: str,
        authorization_artifact_sha256: str,
        gate: str,
        master_head_sha: str,
        deploy_id: str,
        evidence_sha256: str,
        expected_head_version: int,
        expected_previous_evidence_sha256: str | None,
        reason: str,
        now: datetime | None = None,
    ) -> AcceptancePublicationAuthorization:
        """Resolve locally and match every publication binding exactly."""

        digest = validate_publication_authorization_reference(
            authorization_artifact_uri, authorization_artifact_sha256
        )
        _validate_bindings(
            gate=gate,
            master_head_sha=master_head_sha,
            deploy_id=deploy_id,
            evidence_sha256=evidence_sha256,
            expected_head_version=expected_head_version,
            expected_previous_evidence_sha256=(
                expected_previous_evidence_sha256
            ),
            reason=reason,
        )
        record = self.load(digest, now=now)
        expected = {
            "record_type": RECORD_TYPE,
            "action": ACTION,
            "operation": OPERATION,
            "gate": gate,
            "environment": ENVIRONMENT,
            "repository": REPOSITORY,
            "master_head_sha": master_head_sha,
            "deploy_id": deploy_id,
            "evidence_sha256": evidence_sha256,
            "expected_head_version": expected_head_version,
            "expected_previous_evidence_sha256": (
                expected_previous_evidence_sha256
            ),
            "reason": reason,
        }
        if any(record.payload.get(key) != value for key, value in expected.items()):
            raise AcceptancePublicationAuthorizationInvalid(
                "publication authorization bindings do not match"
            )
        return record

    def _decode_record(
        self,
        record: LedgerRecord,
        identity: LedgerRecord,
        *,
        expected_digest: str,
        now: datetime,
    ) -> AcceptancePublicationAuthorization:
        if (
            record.version != 1
            or record.record_id != _record_id(expected_digest)
            or record.tenant_id != AUTHORIZATION_TENANT_ID
            or record.kind != AUTHORIZATION_KIND
            or record.parent_ids != ()
            or record.source != "acceptance_publication_authorization"
            or record.trace_id != expected_digest
        ):
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization traceability is invalid"
            )
        identity_payload = _validate_identity_binding_record(
            identity,
            expected_digest=expected_digest,
            content_record_id=record.record_id,
        )
        actor_tenant_id = str(identity_payload["actor_tenant_id"])
        actor_account_id = str(identity_payload["actor_account_id"])
        if actor_tenant_id != self._primary_tenant_id:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization tenant identity is invalid"
            )
        payload = _validate_payload(
            record.payload,
            primary_tenant_id=self._primary_tenant_id,
            actor_account_id=actor_account_id,
            pseudonymizer=self._pseudonymizer,
        )
        actor = payload["authorized_by"]
        assert isinstance(actor, Mapping)
        if actor.get("pseudonym_key_id") != identity_payload.get(
            "pseudonym_key_id"
        ):
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization identity binding does not match public evidence"
            )
        expected_binding = _private_content_binding_hmac(
            self._pseudonymizer,
            authorization_sha256=expected_digest,
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
            pseudonym_key_id=str(identity_payload["pseudonym_key_id"]),
        )
        if not hmac.compare_digest(
            str(identity_payload.get("content_binding_hmac")), expected_binding
        ):
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization private content binding is invalid"
            )
        try:
            canonical = _canonical_json_bytes(payload)
        except AcceptancePublicationAuthorizationInvalid as exc:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization encoding is invalid"
            ) from exc
        if hashlib.sha256(canonical).hexdigest() != expected_digest:
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization digest is invalid"
            )
        authorized_at = _parse_utc(
            payload["authorized_at_utc"], "authorization timestamp"
        )
        expires_at = _parse_utc(payload["expires_at_utc"], "expiry timestamp")
        if expires_at - authorized_at != timedelta(
            seconds=AUTHORIZATION_TTL_SECONDS
        ):
            raise AcceptancePublicationAuthorizationUnavailable(
                "publication authorization TTL is invalid"
            )
        if now < authorized_at:
            raise AcceptancePublicationAuthorizationNotFound(
                "publication authorization is not active"
            )
        if now >= expires_at:
            raise AcceptancePublicationAuthorizationNotFound(
                "publication authorization has expired"
            )
        return AcceptancePublicationAuthorization(
            sha256=expected_digest,
            uri=acceptance_publication_authorization_url(expected_digest),
            body=canonical,
            payload=payload,
            expires_at=expires_at,
        )


def validate_publication_authorization_reference(
    artifact_uri: Any, artifact_sha256: Any
) -> str:
    """Validate an exact local-record URI/hash pair without dereferencing it."""

    if not isinstance(artifact_uri, str) or not isinstance(artifact_sha256, str):
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization reference is invalid"
        )
    match = _URI_RE.fullmatch(artifact_uri)
    if (
        match is None
        or _SHA256_RE.fullmatch(artifact_sha256) is None
        or match.group("authorization_sha256") != artifact_sha256
    ):
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization reference is invalid"
        )
    return artifact_sha256


def _validate_bindings(
    *,
    gate: Any,
    master_head_sha: Any,
    deploy_id: Any,
    evidence_sha256: Any,
    expected_head_version: Any,
    expected_previous_evidence_sha256: Any,
    reason: Any,
) -> None:
    if gate not in ACCEPTANCE_AUTHORITY_PATH_BY_GATE:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization gate is invalid"
        )
    if not isinstance(master_head_sha, str) or _SHA1_RE.fullmatch(master_head_sha) is None:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization master commit is invalid"
        )
    if not isinstance(deploy_id, str) or _DEPLOY_ID_RE.fullmatch(deploy_id) is None:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization deploy ID is invalid"
        )
    if not isinstance(evidence_sha256, str) or _SHA256_RE.fullmatch(evidence_sha256) is None:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization evidence digest is invalid"
        )
    if (
        not isinstance(expected_head_version, int)
        or isinstance(expected_head_version, bool)
        or expected_head_version < 0
    ):
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization head version is invalid"
        )
    if expected_head_version == 0:
        if expected_previous_evidence_sha256 is not None:
            raise AcceptancePublicationAuthorizationInvalid(
                "initial publication authorization predecessor is invalid"
            )
    elif (
        not isinstance(expected_previous_evidence_sha256, str)
        or _SHA256_RE.fullmatch(expected_previous_evidence_sha256) is None
    ):
        raise AcceptancePublicationAuthorizationInvalid(
            "replacement publication authorization predecessor is invalid"
        )
    if reason != REASON:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization reason is invalid"
        )


def _validate_payload(
    payload: Mapping[str, Any],
    *,
    primary_tenant_id: str,
    actor_account_id: str,
    pseudonymizer: CustomerProductionPseudonymizer,
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != _RECORD_KEYS:
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization schema is invalid"
        )
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("record_type") != RECORD_TYPE
        or payload.get("action") != ACTION
        or payload.get("operation") != OPERATION
        or payload.get("environment") != ENVIRONMENT
        or payload.get("repository") != REPOSITORY
    ):
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization identity is invalid"
        )
    try:
        _validate_bindings(
            gate=payload.get("gate"),
            master_head_sha=payload.get("master_head_sha"),
            deploy_id=payload.get("deploy_id"),
            evidence_sha256=payload.get("evidence_sha256"),
            expected_head_version=payload.get("expected_head_version"),
            expected_previous_evidence_sha256=payload.get(
                "expected_previous_evidence_sha256"
            ),
            reason=payload.get("reason"),
        )
    except AcceptancePublicationAuthorizationInvalid as exc:
        raise AcceptancePublicationAuthorizationUnavailable(str(exc)) from exc
    actor = payload.get("authorized_by")
    if not isinstance(actor, Mapping) or set(actor) != _ACTOR_KEYS:
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization actor is invalid"
        )
    try:
        key_id = validate_public_pseudonym_metadata(
            actor, available_key_ids=pseudonymizer.key_ids
        )
        validate_public_pseudonym_subject(actor.get("tenant_subject"))
        validate_public_pseudonym_subject(actor.get("account_subject"))
        pseudonymizer.assert_subject(
            actor.get("tenant_subject"),
            domain=PUBLICATION_TENANT_DOMAIN,
            tenant_scope=primary_tenant_id,
            value=primary_tenant_id,
            key_id=key_id,
        )
        pseudonymizer.assert_subject(
            actor.get("account_subject"),
            domain=PUBLICATION_ACCOUNT_DOMAIN,
            tenant_scope=primary_tenant_id,
            value=actor_account_id,
            key_id=key_id,
        )
    except ValueError as exc:
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization actor is invalid"
        ) from exc
    if actor.get("role") != "owner":
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization actor is invalid"
        )
    _parse_utc(payload.get("authorized_at_utc"), "authorization timestamp")
    _parse_utc(payload.get("expires_at_utc"), "expiry timestamp")
    return payload


def _record_id(digest: str) -> str:
    return f"acceptance-publication-authorization-{digest}"


def _identity_binding_record_id(digest: str) -> str:
    return f"acceptance-publication-authorization-identity-{digest}"


def _private_content_binding_hmac(
    pseudonymizer: CustomerProductionPseudonymizer,
    *,
    authorization_sha256: str,
    actor_tenant_id: str,
    actor_account_id: str,
    pseudonym_key_id: str,
) -> str:
    facts = _canonical_json_bytes(
        {
            "authorization_sha256": authorization_sha256,
            "actor_tenant_id": actor_tenant_id,
            "actor_account_id": actor_account_id,
            "pseudonym_key_id": pseudonym_key_id,
        }
    ).decode("ascii")
    return pseudonymizer.subject(
        domain=PUBLICATION_CONTENT_BINDING_DOMAIN,
        tenant_scope=actor_tenant_id,
        value=facts,
        key_id=pseudonym_key_id,
    )


def _validate_identity_binding_record(
    record: LedgerRecord | None,
    *,
    expected_digest: str,
    content_record_id: str,
    expected_payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if (
        record is None
        or record.version != 1
        or record.tenant_id != AUTHORIZATION_TENANT_ID
        or record.kind != IDENTITY_BINDING_KIND
        or record.record_id != _identity_binding_record_id(expected_digest)
        or record.parent_ids != (content_record_id,)
        or record.source != "acceptance_publication_authorization"
        or record.trace_id != expected_digest
        or not isinstance(record.payload, Mapping)
        or set(record.payload) != _IDENTITY_BINDING_KEYS
        or record.payload.get("schema_version") != IDENTITY_BINDING_SCHEMA_VERSION
        or record.payload.get("authorization_sha256") != expected_digest
        or record.payload.get("actor_tenant_id") is None
        or _TENANT_ID_RE.fullmatch(str(record.payload.get("actor_tenant_id"))) is None
        or _ACCOUNT_ID_RE.fullmatch(str(record.payload.get("actor_account_id") or ""))
        is None
        or not isinstance(record.payload.get("pseudonym_key_id"), str)
        or not isinstance(record.payload.get("content_binding_hmac"), str)
    ):
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization identity binding is invalid"
        )
    if expected_payload is not None and dict(record.payload) != dict(expected_payload):
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization identity binding conflicted"
        )
    try:
        validate_public_pseudonym_subject(record.payload.get("content_binding_hmac"))
    except ValueError as exc:
        raise AcceptancePublicationAuthorizationUnavailable(
            "publication authorization identity binding is invalid"
        ) from exc
    return record.payload


def _utc_now(value: datetime | None) -> datetime:
    stamp = datetime.now(UTC) if value is None else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization time must be timezone-aware"
        )
    return stamp.astimezone(UTC).replace(microsecond=0)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or _UTC_RE.fullmatch(value) is None:
        raise AcceptancePublicationAuthorizationUnavailable(f"{field} is invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise AcceptancePublicationAuthorizationUnavailable(
            f"{field} is invalid"
        ) from exc
    return parsed


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise AcceptancePublicationAuthorizationInvalid(
            "publication authorization is not strict JSON"
        ) from exc


__all__ = [
    "ACTION",
    "AUTHORIZATION_KIND",
    "AUTHORIZATION_TENANT_ID",
    "AUTHORIZATION_TTL_SECONDS",
    "AcceptancePublicationAuthorization",
    "AcceptancePublicationAuthorizationInvalid",
    "AcceptancePublicationAuthorizationNotFound",
    "AcceptancePublicationAuthorizationStore",
    "AcceptancePublicationAuthorizationUnavailable",
    "OPERATION",
    "REASON",
    "RECORD_TYPE",
    "SCHEMA_VERSION",
    "validate_publication_authorization_reference",
]
