"""Authenticated, content-addressed human attestations for production acceptance.

The acceptance evidence document may reference these records, but it cannot
create them.  Actor identity and the account role are server-derived.  The
functional attestation role is accepted only through the fixed mapping below,
so a request body cannot promote a member into legal, operations, security, or
release authority.

Attestation bytes are immutable StateStore rows addressed by their canonical
SHA-256.  A separate version-checked status row supplies explicit revocation;
every read revalidates both rows.  No list/head endpoint exists.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
import re
from types import MappingProxyType
from typing import Any

from api.acceptance_authority_contract import PRODUCTION_API_ORIGIN
from api.services.production.state_substrate import LedgerRecord, StateStore, VersionConflict


SCHEMA_VERSION = "cas_harness_human_attestation.v2"
STATUS_SCHEMA_VERSION = "cas_harness_human_attestation_status.v2"
IDENTITY_BINDING_SCHEMA_VERSION = (
    "cas_harness_human_attestation_identity_binding.v1"
)
RECORD_TYPE = "human_attestation"
ACTION = "ATTEST"
ENVIRONMENT = "public-production"
REPOSITORY = "LittleHenderson/noetic-compass"
ATTESTATION_TENANT_ID = "cas-harness-customer-production-human-attestations"
ATTESTATION_KIND = "customer_production_human_attestation"
STATUS_KIND = "customer_production_human_attestation_status"
IDENTITY_BINDING_KIND = "customer_production_human_attestation_identity_binding"
PUBLIC_PATH_PREFIX = "/internal/human-attestations/"
PUBLIC_PATH_PATTERN = re.compile(
    r"^/internal/human-attestations/(?P<attestation_sha256>[0-9a-f]{64})$"
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DEPLOY_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
_ACCOUNT_RE = re.compile(r"^acct-[0-9a-f]{32}$")
_PSEUDONYM_RE = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")
_KEY_ID_RE = re.compile(r"^hatk_[0-9a-f]{32}$")
_KEY_SECRET_PREFIX = "base64url:"
_MIN_PSEUDONYM_KEY_BYTES = 32
_MAX_PSEUDONYM_KEY_BYTES = 64

PSEUDONYMIZATION_SCHEME = "hmac-sha256-tenant-scoped-v1"
PUBLIC_HUMAN_ASSURANCE_BOUNDARY: Mapping[str, str] = MappingProxyType(
    {
        "schema_version": "cas_harness_human_assurance_boundary.v1",
        "account_identity": "authenticated_platform_account",
        "functional_role": "self_asserted_platform_role_authorized",
        "natural_person_identity": "unverified",
        "professional_qualification": "unverified",
        "distinct_natural_persons": "unverified",
        "qualification_authority": "unavailable",
        "distinctness_authority": "unavailable",
    }
)

# Exact functional role -> exact live account role.  This is deliberately not
# a caller-widenable set.  Professional qualification remains a human/legal
# fact; this mapping proves which authenticated platform identity made the
# attestation and prevents a body-only role claim.
ATTESTATION_ACCOUNT_ROLE: Mapping[str, str] = {
    "legal_counsel": "owner",
    "privacy_owner": "admin",
    "product_owner": "owner",
    "legal_owner": "admin",
    "research_owner": "operator",
    "incident_commander": "owner",
    "legal": "admin",
    "operations": "operator",
    "security": "admin",
    "support": "support",
    "operations_owner": "operator",
    "security_owner": "admin",
}

PURPOSE_GATE_ROLES: Mapping[str, tuple[str, frozenset[str]]] = {
    "legal_approval": (
        "legal_publication_approval",
        frozenset({"legal_counsel", "privacy_owner", "product_owner"}),
    ),
    "claim_approval": (
        "claim_honesty",
        frozenset({"legal_owner", "product_owner", "research_owner"}),
    ),
    "incident_postmortem": (
        "incident_tabletop",
        frozenset({"incident_commander"}),
    ),
    "incident_closure": (
        "incident_tabletop",
        frozenset({"incident_commander", "operations", "security"}),
    ),
    "tabletop_evidence": (
        "incident_tabletop",
        frozenset({"incident_commander"}),
    ),
    "tabletop_completion": (
        "incident_tabletop",
        frozenset({"incident_commander", "legal", "operations", "security", "support"}),
    ),
    "release_decision_record": (
        "release_decision",
        frozenset({"product_owner"}),
    ),
    "release_approval": (
        "release_decision",
        frozenset({"legal_owner", "operations_owner", "product_owner", "security_owner"}),
    ),
}

# Aggregate records are still created by one authenticated actor, but they are
# accepted only when they recursively pin the exact individual attestations
# below.  This avoids pretending that one login can speak for four or five
# people while preserving one shared content-addressed schema.
SUPPORT_REQUIREMENTS: Mapping[str, tuple[str, frozenset[str]]] = {
    "incident_postmortem": (
        "incident_closure",
        frozenset({"incident_commander", "operations", "security"}),
    ),
    "tabletop_evidence": (
        "tabletop_completion",
        frozenset({"incident_commander", "legal", "operations", "security", "support"}),
    ),
    "release_decision_record": (
        "release_approval",
        frozenset({"legal_owner", "operations_owner", "product_owner", "security_owner"}),
    ),
}

_SUPPORT_KEYS = frozenset(
    {"role", "attestation_artifact_uri", "attestation_sha256", "attested_at_utc"}
)

_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "action",
        "purpose",
        "gate",
        "environment",
        "repository",
        "master_head_sha",
        "deploy_id",
        "evidence_binding_sha256",
        "attested_at_utc",
        "actor",
        "supporting_attestations",
    }
)
_ACTOR_KEYS = frozenset(
    {
        "tenant_subject",
        "account_subject",
        "pseudonymization_scheme",
        "pseudonym_key_id",
        "account_role",
        "attestation_role",
        "assurance_boundary",
    }
)
_ASSURANCE_KEYS = frozenset(PUBLIC_HUMAN_ASSURANCE_BOUNDARY)
_IDENTITY_BINDING_KEYS = frozenset(
    {
        "schema_version",
        "attestation_sha256",
        "actor_tenant_id",
        "actor_account_id",
        "pseudonym_key_id",
        "content_binding_hmac",
    }
)
_STATUS_KEYS = frozenset(
    {
        "schema_version",
        "attestation_sha256",
        "active",
        "revoked_at_utc",
        "pseudonym_key_id",
        "content_binding_hmac",
        "revoked_by_account_subject",
    }
)


class HumanAttestationError(RuntimeError):
    """Base class for secret-safe human-attestation failures."""


class HumanAttestationInvalid(HumanAttestationError):
    """The requested or stored attestation is malformed or unauthorized."""


class HumanAttestationNotFound(HumanAttestationError):
    """The exact attestation is absent or revoked."""


class HumanAttestationUnavailable(HumanAttestationError):
    """Durable attestation state failed integrity or availability checks."""


@dataclass(frozen=True, slots=True)
class HumanAttestation:
    sha256: str
    uri: str
    body: bytes
    payload: Mapping[str, Any]
    # Private durable bindings used for authorization and cross-key account
    # equality. They are never serialized into ``body`` or returned publicly.
    actor_tenant_id: str
    actor_account_id: str


def human_attestation_url(attestation_sha256: str) -> str:
    if _SHA256_RE.fullmatch(attestation_sha256) is None:
        raise ValueError("attestation_sha256 must be lowercase SHA-256")
    return f"{PRODUCTION_API_ORIGIN}{PUBLIC_PATH_PREFIX}{attestation_sha256}"


def parse_human_attestation_pseudonym_keyring(
    raw_json: str, *, active_key_id: str
) -> Mapping[str, bytes]:
    """Parse a dedicated rotation-aware keyring without logging secret material.

    Every JSON value must be ``base64url:`` followed by the canonical unpadded
    base64url encoding of 32--64 independently generated random bytes. Key IDs
    are non-secret opaque 128-bit labels in ``hatk_<32 lowercase hex>`` form;
    descriptive, account-like, email-like, or otherwise PII-bearing IDs are
    deliberately outside the accepted grammar.
    """

    if not isinstance(raw_json, str) or not raw_json:
        raise ValueError("human attestation pseudonym keyring is required")
    if _KEY_ID_RE.fullmatch(active_key_id or "") is None:
        raise ValueError("human attestation active pseudonym key id is invalid")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("human attestation pseudonym keyring has duplicate keys")
            result[key] = value
        return result

    try:
        decoded = json.loads(raw_json, object_pairs_hook=reject_duplicates)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("human attestation pseudonym keyring is invalid") from exc
    if not isinstance(decoded, dict) or not (1 <= len(decoded) <= 16):
        raise ValueError("human attestation pseudonym keyring is invalid")
    parsed: dict[str, bytes] = {}
    seen_keys: set[bytes] = set()
    for key_id, secret in decoded.items():
        if not isinstance(key_id, str) or _KEY_ID_RE.fullmatch(key_id) is None:
            raise ValueError("human attestation pseudonym keyring is invalid")
        if not isinstance(secret, str):
            raise ValueError("human attestation pseudonym keyring is invalid")
        key = _decode_pseudonym_key_secret(secret)
        if key in seen_keys:
            raise ValueError("human attestation pseudonym keyring is invalid")
        parsed[key_id] = key
        seen_keys.add(key)
    if active_key_id not in parsed:
        raise ValueError("human attestation active pseudonym key is unavailable")
    return MappingProxyType(parsed)


def human_attestation_pseudonym_key_matches_secret(
    key: bytes, candidate: str
) -> bool:
    """Return whether another configured secret reuses this key material.

    The comparison covers raw UTF-8 bytes plus both accepted external base64url
    spellings, and returns only a boolean so callers never need to log a key.
    """

    _validate_pseudonym_key_material(key)
    if not isinstance(candidate, str) or not candidate:
        return False
    candidate_bytes = candidate.encode("utf-8")
    external = _encode_pseudonym_key_secret(key)
    payload = external.removeprefix(_KEY_SECRET_PREFIX)
    return any(
        hmac.compare_digest(candidate_bytes, form)
        for form in (
            key,
            external.encode("ascii"),
            payload.encode("ascii"),
        )
    )


class HumanAttestationStore:
    """Create-only attestation bytes plus version-checked revocation status."""

    def __init__(
        self,
        store: StateStore,
        *,
        primary_tenant_id: str,
        pseudonym_keyring: Mapping[str, bytes],
        active_pseudonym_key_id: str,
    ) -> None:
        if not isinstance(primary_tenant_id, str) or not primary_tenant_id.strip():
            raise ValueError("primary_tenant_id is required")
        if _KEY_ID_RE.fullmatch(active_pseudonym_key_id or "") is None:
            raise ValueError("active_pseudonym_key_id is invalid")
        if not isinstance(pseudonym_keyring, Mapping) or not (
            1 <= len(pseudonym_keyring) <= 16
        ):
            raise ValueError("pseudonym_keyring is invalid")
        keys: dict[str, bytes] = {}
        seen_keys: set[bytes] = set()
        for key_id, key in pseudonym_keyring.items():
            if (
                not isinstance(key_id, str)
                or _KEY_ID_RE.fullmatch(key_id) is None
                or not isinstance(key, bytes)
                or key in seen_keys
            ):
                raise ValueError("pseudonym_keyring is invalid")
            _validate_pseudonym_key_material(key)
            keys[key_id] = key
            seen_keys.add(key)
        if active_pseudonym_key_id not in keys:
            raise ValueError("active pseudonym key is unavailable")
        self._store = store
        self._primary_tenant_id = primary_tenant_id
        self._pseudonym_keys = MappingProxyType(keys)
        self._active_pseudonym_key_id = active_pseudonym_key_id

    def create(
        self,
        *,
        actor_tenant_id: str,
        actor_account_id: str,
        actor_account_role: str,
        purpose: str,
        gate: str,
        attestation_role: str,
        master_head_sha: str,
        deploy_id: str,
        evidence_binding_sha256: str,
        supporting_attestations: list[Mapping[str, Any]] | None = None,
        now: datetime | None = None,
    ) -> HumanAttestation:
        if actor_tenant_id != self._primary_tenant_id:
            raise HumanAttestationInvalid("the primary tenant is required")
        if _ACCOUNT_RE.fullmatch(actor_account_id or "") is None:
            raise HumanAttestationInvalid("the authenticated account is invalid")
        expected = PURPOSE_GATE_ROLES.get(purpose)
        if expected is None or gate != expected[0] or attestation_role not in expected[1]:
            raise HumanAttestationInvalid("attestation purpose, gate, and role do not match")
        if ATTESTATION_ACCOUNT_ROLE.get(attestation_role) != actor_account_role:
            raise HumanAttestationInvalid("the authenticated account role cannot attest this role")
        if _SHA1_RE.fullmatch(master_head_sha or "") is None:
            raise HumanAttestationInvalid("master_head_sha is invalid")
        if _DEPLOY_RE.fullmatch(deploy_id or "") is None:
            raise HumanAttestationInvalid("deploy_id is invalid")
        if _SHA256_RE.fullmatch(evidence_binding_sha256 or "") is None:
            raise HumanAttestationInvalid("evidence binding is invalid")
        stamp = _utc_now(now)
        supports = self._validate_supporting_references(
            purpose=purpose,
            gate=gate,
            master_head_sha=master_head_sha,
            deploy_id=deploy_id,
            evidence_binding_sha256=evidence_binding_sha256,
            supporting_attestations=supporting_attestations or [],
            now=stamp,
        )
        stamp_text = _format_utc(stamp)
        key_id = self._active_pseudonym_key_id
        key = self._pseudonym_keys[key_id]
        tenant_subject = _tenant_subject(key, actor_tenant_id)
        account_subject = _account_subject(key, actor_tenant_id, actor_account_id)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "action": ACTION,
            "purpose": purpose,
            "gate": gate,
            "environment": ENVIRONMENT,
            "repository": REPOSITORY,
            "master_head_sha": master_head_sha,
            "deploy_id": deploy_id,
            "evidence_binding_sha256": evidence_binding_sha256,
            "attested_at_utc": stamp_text,
            "actor": {
                "tenant_subject": tenant_subject,
                "account_subject": account_subject,
                "pseudonymization_scheme": PSEUDONYMIZATION_SCHEME,
                "pseudonym_key_id": key_id,
                "account_role": actor_account_role,
                "attestation_role": attestation_role,
                "assurance_boundary": dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY),
            },
            "supporting_attestations": supports,
        }
        body = _canonical_json_bytes(payload)
        digest = hashlib.sha256(body).hexdigest()
        content_binding_hmac = _private_content_binding_hmac(
            key,
            attestation_sha256=digest,
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
            pseudonym_key_id=key_id,
        )
        record = LedgerRecord.new(
            tenant_id=ATTESTATION_TENANT_ID,
            kind=ATTESTATION_KIND,
            record_id=_attestation_record_id(digest),
            payload=payload,
            source="human_attestation",
            trace_id=digest,
            now=stamp,
        )
        identity_payload = {
            "schema_version": IDENTITY_BINDING_SCHEMA_VERSION,
            "attestation_sha256": digest,
            "actor_tenant_id": actor_tenant_id,
            "actor_account_id": actor_account_id,
            "pseudonym_key_id": key_id,
            "content_binding_hmac": content_binding_hmac,
        }
        identity = LedgerRecord.new(
            tenant_id=ATTESTATION_TENANT_ID,
            kind=IDENTITY_BINDING_KIND,
            record_id=_identity_binding_record_id(digest),
            payload=identity_payload,
            parent_ids=(record.record_id,),
            source="human_attestation",
            trace_id=digest,
            now=stamp,
        )
        status_payload = {
            "schema_version": STATUS_SCHEMA_VERSION,
            "attestation_sha256": digest,
            "active": True,
            "revoked_at_utc": None,
            "pseudonym_key_id": key_id,
            "content_binding_hmac": content_binding_hmac,
            "revoked_by_account_subject": None,
        }
        status = LedgerRecord.new(
            tenant_id=ATTESTATION_TENANT_ID,
            kind=STATUS_KIND,
            record_id=_status_record_id(digest),
            payload=status_payload,
            parent_ids=(record.record_id, identity.record_id),
            source="human_attestation",
            trace_id=digest,
            now=stamp,
        )
        try:
            stored = self._store.put(record, expected_version=0)
        except VersionConflict:
            # A crash can leave the immutable content row present before its
            # separate activation row is committed.  Validate those exact
            # bytes before retrying activation; never strand a valid human
            # action permanently, and never activate corrupt content.
            try:
                existing_record = self._store.get(
                    ATTESTATION_TENANT_ID,
                    ATTESTATION_KIND,
                    _attestation_record_id(digest),
                )
            except Exception as exc:
                raise HumanAttestationUnavailable(
                    "attestation store is unavailable"
                ) from exc
            if (
                existing_record is None
                or existing_record.version != 1
                or existing_record.source != "human_attestation"
                or existing_record.trace_id != digest
                or existing_record.parent_ids
            ):
                raise HumanAttestationUnavailable(
                    "attestation immutability metadata is invalid"
                )
            existing_payload = _validate_payload(
                existing_record.payload,
                expected_digest=digest,
                now=stamp,
                pseudonym_keys=self._pseudonym_keys,
                actor_tenant_id=actor_tenant_id,
                actor_account_id=actor_account_id,
            )
            existing_supports = existing_payload.get("supporting_attestations")
            if not isinstance(existing_supports, list):
                raise HumanAttestationUnavailable(
                    "supporting attestations are invalid"
                )
            self._validate_supporting_references(
                purpose=str(existing_payload["purpose"]),
                gate=str(existing_payload["gate"]),
                master_head_sha=str(existing_payload["master_head_sha"]),
                deploy_id=str(existing_payload["deploy_id"]),
                evidence_binding_sha256=str(
                    existing_payload["evidence_binding_sha256"]
                ),
                supporting_attestations=existing_supports,
                now=stamp,
            )
            if _canonical_json_bytes(existing_payload) != body:
                raise HumanAttestationUnavailable(
                    "content-addressed attestation conflicted"
                )
            stored = existing_record
        except Exception as exc:
            raise HumanAttestationUnavailable("attestation persistence failed") from exc
        if stored.version != 1:
            raise HumanAttestationUnavailable("attestation version is invalid")
        try:
            stored_identity = self._store.put(identity, expected_version=0)
        except VersionConflict:
            try:
                existing_identity = self._store.get(
                    ATTESTATION_TENANT_ID,
                    IDENTITY_BINDING_KIND,
                    _identity_binding_record_id(digest),
                )
            except Exception as exc:
                raise HumanAttestationUnavailable(
                    "attestation identity binding is unavailable"
                ) from exc
            _validate_identity_binding_record(
                existing_identity,
                expected_digest=digest,
                content_record_id=record.record_id,
                expected_payload=identity_payload,
            )
            stored_identity = existing_identity
        except Exception as exc:
            raise HumanAttestationUnavailable(
                "attestation identity binding persistence failed"
            ) from exc
        if stored_identity is None or stored_identity.version != 1:
            raise HumanAttestationUnavailable(
                "attestation identity binding version is invalid"
            )
        try:
            stored_status = self._store.put(status, expected_version=0)
        except VersionConflict:
            try:
                existing = self.load(digest, now=stamp)
            except HumanAttestationNotFound as exc:
                raise HumanAttestationInvalid(
                    "a revoked attestation cannot be reactivated"
                ) from exc
            if existing.body != body:
                raise HumanAttestationUnavailable(
                    "content-addressed attestation conflicted"
                )
            return existing
        except Exception as exc:
            # An unattached immutable record is harmless; without the status row
            # it cannot be served or used by an authority document.
            raise HumanAttestationUnavailable("attestation activation failed") from exc
        if stored_status.version != 1:
            raise HumanAttestationUnavailable("attestation status version is invalid")
        return self.load(digest, now=stamp)

    def _validate_supporting_references(
        self,
        *,
        purpose: str,
        gate: str,
        master_head_sha: str,
        deploy_id: str,
        evidence_binding_sha256: str,
        supporting_attestations: list[Mapping[str, Any]],
        now: datetime,
    ) -> list[dict[str, str]]:
        requirement = SUPPORT_REQUIREMENTS.get(purpose)
        if requirement is None:
            if supporting_attestations:
                raise HumanAttestationInvalid("leaf attestations cannot carry supporting records")
            return []
        child_purpose, expected_roles = requirement
        by_role: dict[str, dict[str, str]] = {}
        actors: set[str] = set()
        for index, reference in enumerate(supporting_attestations):
            if not isinstance(reference, Mapping) or set(reference) != _SUPPORT_KEYS:
                raise HumanAttestationInvalid(
                    f"supporting_attestations[{index}] schema is invalid"
                )
            role = reference.get("role")
            uri = reference.get("attestation_artifact_uri")
            digest = reference.get("attestation_sha256")
            timestamp = reference.get("attested_at_utc")
            if not all(isinstance(value, str) for value in (role, uri, digest, timestamp)):
                raise HumanAttestationInvalid("supporting attestation fields must be strings")
            assert isinstance(role, str) and isinstance(uri, str)
            assert isinstance(digest, str) and isinstance(timestamp, str)
            if role in by_role:
                raise HumanAttestationInvalid("supporting attestation roles must be unique")
            child = self.assert_reference(
                uri=uri,
                sha256=digest,
                purpose=child_purpose,
                gate=gate,
                role=role,
                master_head_sha=master_head_sha,
                deploy_id=deploy_id,
                evidence_binding_sha256=evidence_binding_sha256,
                attested_at_utc=timestamp,
                now=now,
            )
            actor_account_id = child.actor_account_id
            if actor_account_id in actors:
                raise HumanAttestationInvalid(
                    "supporting attestations require distinct authenticated platform "
                    "accounts; account separation does not prove distinct people"
                )
            actors.add(actor_account_id)
            by_role[role] = {
                "role": role,
                "attestation_artifact_uri": uri,
                "attestation_sha256": digest,
                "attested_at_utc": timestamp,
            }
        if frozenset(by_role) != expected_roles:
            raise HumanAttestationInvalid("supporting attestation roles are incomplete")
        return [by_role[role] for role in sorted(by_role)]

    def load(
        self, attestation_sha256: str, *, now: datetime | None = None
    ) -> HumanAttestation:
        if _SHA256_RE.fullmatch(attestation_sha256 or "") is None:
            raise HumanAttestationInvalid("attestation digest is invalid")
        try:
            record = self._store.get(
                ATTESTATION_TENANT_ID,
                ATTESTATION_KIND,
                _attestation_record_id(attestation_sha256),
            )
            identity = self._store.get(
                ATTESTATION_TENANT_ID,
                IDENTITY_BINDING_KIND,
                _identity_binding_record_id(attestation_sha256),
            )
            status = self._store.get(
                ATTESTATION_TENANT_ID,
                STATUS_KIND,
                _status_record_id(attestation_sha256),
            )
        except Exception as exc:
            raise HumanAttestationUnavailable("attestation store is unavailable") from exc
        if record is None or status is None:
            raise HumanAttestationNotFound("attestation is unavailable")
        if identity is None:
            # v1 records have no durable keyed identity provenance and cannot
            # be promoted or served as v2 authority. They must be re-attested.
            raise HumanAttestationUnavailable(
                "keyed attestation identity binding is unavailable"
            )
        if (
            record.version != 1
            or record.source != "human_attestation"
            or record.trace_id != attestation_sha256
            or record.parent_ids
        ):
            raise HumanAttestationUnavailable("attestation immutability metadata is invalid")
        identity_payload = _validate_identity_binding_record(
            identity,
            expected_digest=attestation_sha256,
            content_record_id=record.record_id,
        )
        actor_tenant_id = str(identity_payload["actor_tenant_id"])
        actor_account_id = str(identity_payload["actor_account_id"])
        if actor_tenant_id != self._primary_tenant_id:
            raise HumanAttestationUnavailable(
                "attestation tenant identity is invalid"
            )
        payload = _validate_payload(
            record.payload,
            expected_digest=attestation_sha256,
            now=_utc_now(now),
            pseudonym_keys=self._pseudonym_keys,
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
        )
        actor = payload["actor"]
        assert isinstance(actor, Mapping)
        identity_key_id = str(identity_payload["pseudonym_key_id"])
        if identity_key_id != actor["pseudonym_key_id"]:
            raise HumanAttestationUnavailable(
                "attestation identity binding does not match public evidence"
            )
        identity_key = self._pseudonym_keys.get(identity_key_id)
        if identity_key is None:
            raise HumanAttestationUnavailable(
                "attestation pseudonym verification key is unavailable"
            )
        expected_content_binding = _private_content_binding_hmac(
            identity_key,
            attestation_sha256=attestation_sha256,
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
            pseudonym_key_id=identity_key_id,
        )
        if not hmac.compare_digest(
            str(identity_payload["content_binding_hmac"]),
            expected_content_binding,
        ):
            raise HumanAttestationUnavailable(
                "attestation private content binding is invalid"
            )
        _validate_status(
            status,
            attestation_sha256,
            record.record_id,
            identity.record_id,
            identity_key_id,
            expected_content_binding,
        )
        if status.payload.get("active") is not True:
            raise HumanAttestationNotFound("attestation is revoked")
        supports = payload.get("supporting_attestations")
        if not isinstance(supports, list):  # payload validation already guards this
            raise HumanAttestationUnavailable("supporting attestations are invalid")
        self._validate_supporting_references(
            purpose=str(payload["purpose"]),
            gate=str(payload["gate"]),
            master_head_sha=str(payload["master_head_sha"]),
            deploy_id=str(payload["deploy_id"]),
            evidence_binding_sha256=str(payload["evidence_binding_sha256"]),
            supporting_attestations=supports,
            now=_utc_now(now),
        )
        body = _canonical_json_bytes(payload)
        return HumanAttestation(
            sha256=attestation_sha256,
            uri=human_attestation_url(attestation_sha256),
            body=body,
            payload=payload,
            actor_tenant_id=actor_tenant_id,
            actor_account_id=actor_account_id,
        )

    def revoke(
        self,
        attestation_sha256: str,
        *,
        actor_tenant_id: str,
        actor_account_id: str,
        actor_account_role: str,
        now: datetime | None = None,
    ) -> bool:
        if (
            actor_tenant_id != self._primary_tenant_id
            or _ACCOUNT_RE.fullmatch(actor_account_id or "") is None
        ):
            raise HumanAttestationInvalid("the authenticated primary-tenant account is invalid")
        current = self.load(attestation_sha256, now=now)
        original_actor = current.payload["actor"]
        assert isinstance(original_actor, Mapping)
        if current.actor_account_id != actor_account_id and actor_account_role != "owner":
            raise HumanAttestationInvalid("only the original actor or a primary owner may revoke")
        key_id = str(original_actor["pseudonym_key_id"])
        key = self._pseudonym_keys.get(key_id)
        if key is None:
            raise HumanAttestationUnavailable(
                "attestation pseudonym verification key is unavailable"
            )
        revoker_subject = _account_subject(key, actor_tenant_id, actor_account_id)
        try:
            status = self._store.get(
                ATTESTATION_TENANT_ID, STATUS_KIND, _status_record_id(attestation_sha256)
            )
        except Exception as exc:
            raise HumanAttestationUnavailable("attestation status is unavailable") from exc
        if status is None:
            raise HumanAttestationUnavailable("attestation status is unavailable")
        stamp = _utc_now(now)
        replacement = status.with_payload(
            {
                "schema_version": STATUS_SCHEMA_VERSION,
                "attestation_sha256": attestation_sha256,
                "active": False,
                "revoked_at_utc": _format_utc(stamp),
                "pseudonym_key_id": key_id,
                "content_binding_hmac": str(
                    status.payload["content_binding_hmac"]
                ),
                "revoked_by_account_subject": revoker_subject,
            },
            now=stamp,
        )
        try:
            self._store.put(replacement, expected_version=status.version)
        except VersionConflict as exc:
            raise HumanAttestationUnavailable("attestation status changed; retry safely") from exc
        except Exception as exc:
            raise HumanAttestationUnavailable("attestation revocation failed") from exc
        return True

    def assert_reference(
        self,
        *,
        uri: str,
        sha256: str,
        purpose: str,
        gate: str,
        role: str,
        master_head_sha: str,
        deploy_id: str,
        evidence_binding_sha256: str,
        attested_at_utc: str | None = None,
        now: datetime | None = None,
    ) -> HumanAttestation:
        if _SHA256_RE.fullmatch(sha256 or "") is None:
            raise HumanAttestationInvalid("attestation digest is invalid")
        if uri != human_attestation_url(sha256):
            raise HumanAttestationInvalid("attestation URI is not content-addressed")
        record = self.load(sha256, now=now)
        payload = record.payload
        exact = {
            "purpose": purpose,
            "gate": gate,
            "master_head_sha": master_head_sha,
            "deploy_id": deploy_id,
            "evidence_binding_sha256": evidence_binding_sha256,
        }
        if any(payload.get(key) != value for key, value in exact.items()):
            raise HumanAttestationInvalid("attestation binding does not match evidence")
        actor = payload.get("actor")
        if not isinstance(actor, Mapping) or actor.get("attestation_role") != role:
            raise HumanAttestationInvalid("attestation actor role does not match evidence")
        if attested_at_utc is not None and payload.get("attested_at_utc") != attested_at_utc:
            raise HumanAttestationInvalid("attestation timestamp does not match evidence")
        return record


def _validate_payload(
    value: Mapping[str, Any],
    *,
    expected_digest: str,
    now: datetime,
    pseudonym_keys: Mapping[str, bytes],
    actor_tenant_id: str,
    actor_account_id: str,
) -> Mapping[str, Any]:
    if set(value) != _RECORD_KEYS or not isinstance(value.get("actor"), Mapping):
        raise HumanAttestationUnavailable("attestation schema is invalid")
    actor = value["actor"]
    assert isinstance(actor, Mapping)
    assurance = actor.get("assurance_boundary")
    if (
        set(actor) != _ACTOR_KEYS
        or not isinstance(assurance, Mapping)
        or set(assurance) != _ASSURANCE_KEYS
        or dict(assurance) != dict(PUBLIC_HUMAN_ASSURANCE_BOUNDARY)
    ):
        raise HumanAttestationUnavailable("attestation actor schema is invalid")
    supports = value.get("supporting_attestations")
    if not isinstance(supports, list) or any(
        not isinstance(item, Mapping) or set(item) != _SUPPORT_KEYS
        for item in supports
    ):
        raise HumanAttestationUnavailable("supporting attestation schema is invalid")
    purpose = value.get("purpose")
    gate = value.get("gate")
    role = actor.get("attestation_role")
    expected = PURPOSE_GATE_ROLES.get(str(purpose))
    key_id = actor.get("pseudonym_key_id")
    key = pseudonym_keys.get(str(key_id)) if isinstance(key_id, str) else None
    if isinstance(key_id, str) and _KEY_ID_RE.fullmatch(key_id) is not None and key is None:
        raise HumanAttestationUnavailable(
            "attestation pseudonym verification key is unavailable"
        )
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("record_type") != RECORD_TYPE
        or value.get("action") != ACTION
        or value.get("environment") != ENVIRONMENT
        or value.get("repository") != REPOSITORY
        or expected is None
        or gate != expected[0]
        or role not in expected[1]
        or ATTESTATION_ACCOUNT_ROLE.get(str(role)) != actor.get("account_role")
        or _SHA1_RE.fullmatch(str(value.get("master_head_sha") or "")) is None
        or _DEPLOY_RE.fullmatch(str(value.get("deploy_id") or "")) is None
        or _SHA256_RE.fullmatch(str(value.get("evidence_binding_sha256") or "")) is None
        or actor.get("pseudonymization_scheme") != PSEUDONYMIZATION_SCHEME
        or _KEY_ID_RE.fullmatch(str(key_id or "")) is None
        or _PSEUDONYM_RE.fullmatch(str(actor.get("tenant_subject") or "")) is None
        or _PSEUDONYM_RE.fullmatch(str(actor.get("account_subject") or "")) is None
        or not isinstance(actor_tenant_id, str)
        or not actor_tenant_id
        or _ACCOUNT_RE.fullmatch(actor_account_id or "") is None
    ):
        raise HumanAttestationUnavailable("attestation content is invalid")
    stamp = _parse_utc(value.get("attested_at_utc"))
    if stamp > now:
        raise HumanAttestationUnavailable("attestation timestamp is in the future")
    body = _canonical_json_bytes(value)
    if hashlib.sha256(body).hexdigest() != expected_digest:
        raise HumanAttestationUnavailable("attestation digest does not match canonical bytes")
    assert key is not None and isinstance(key_id, str)
    expected_tenant_subject = _tenant_subject(key, actor_tenant_id)
    expected_account_subject = _account_subject(
        key, actor_tenant_id, actor_account_id
    )
    if not (
        hmac.compare_digest(
            str(actor["tenant_subject"]), expected_tenant_subject
        )
        and hmac.compare_digest(
            str(actor["account_subject"]), expected_account_subject
        )
    ):
        raise HumanAttestationUnavailable(
            "attestation keyed identity binding is invalid"
        )
    return value


def _validate_identity_binding_record(
    record: LedgerRecord | None,
    *,
    expected_digest: str,
    content_record_id: str,
    expected_payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if record is None:
        raise HumanAttestationUnavailable(
            "attestation identity binding is unavailable"
        )
    value = record.payload
    if (
        record.version != 1
        or record.source != "human_attestation"
        or record.trace_id != expected_digest
        or record.parent_ids != (content_record_id,)
        or set(value) != _IDENTITY_BINDING_KEYS
        or value.get("schema_version") != IDENTITY_BINDING_SCHEMA_VERSION
        or value.get("attestation_sha256") != expected_digest
        or not isinstance(value.get("actor_tenant_id"), str)
        or not value.get("actor_tenant_id")
        or _ACCOUNT_RE.fullmatch(str(value.get("actor_account_id") or "")) is None
        or _KEY_ID_RE.fullmatch(str(value.get("pseudonym_key_id") or "")) is None
        or _PSEUDONYM_RE.fullmatch(
            str(value.get("content_binding_hmac") or "")
        )
        is None
    ):
        raise HumanAttestationUnavailable(
            "attestation identity binding is invalid"
        )
    if expected_payload is not None and dict(value) != dict(expected_payload):
        raise HumanAttestationUnavailable(
            "attestation identity binding conflicted"
        )
    return value


def _validate_status(
    status: LedgerRecord,
    expected_digest: str,
    content_record_id: str,
    identity_record_id: str,
    pseudonym_key_id: str,
    content_binding_hmac: str,
) -> None:
    value = status.payload
    if (
        set(value) != _STATUS_KEYS
        or value.get("schema_version") != STATUS_SCHEMA_VERSION
        or value.get("attestation_sha256") != expected_digest
        or not isinstance(value.get("active"), bool)
        or value.get("pseudonym_key_id") != pseudonym_key_id
        or not hmac.compare_digest(
            str(value.get("content_binding_hmac") or ""),
            content_binding_hmac,
        )
        or status.source != "human_attestation"
        or status.trace_id != expected_digest
        or status.parent_ids != (content_record_id, identity_record_id)
    ):
        raise HumanAttestationUnavailable("attestation status is invalid")
    if value.get("active") is True:
        if (
            status.version != 1
            or value.get("revoked_at_utc") is not None
            or value.get("revoked_by_account_subject") is not None
        ):
            raise HumanAttestationUnavailable("active attestation carries revocation fields")
    else:
        if status.version != 2:
            raise HumanAttestationUnavailable("revoked attestation version is invalid")
        _parse_utc(value.get("revoked_at_utc"))
        if _PSEUDONYM_RE.fullmatch(
            str(value.get("revoked_by_account_subject") or "")
        ) is None:
            raise HumanAttestationUnavailable("revocation actor is invalid")


def _attestation_record_id(digest: str) -> str:
    return f"attestation-{digest}"


def _status_record_id(digest: str) -> str:
    return f"attestation-status-{digest}"


def _identity_binding_record_id(digest: str) -> str:
    return f"attestation-identity-{digest}"


def _hmac_subject(key: bytes, domain: str, *parts: str) -> str:
    message = (
        "cas-harness-human-attestation/v2\0"
        + domain
        + "\0"
        + "\0".join(parts)
    ).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def _tenant_subject(key: bytes, tenant_id: str) -> str:
    return _hmac_subject(key, "tenant-subject", tenant_id)


def _account_subject(key: bytes, tenant_id: str, account_id: str) -> str:
    # Tenant is inside the MAC input, so the same platform account identifier
    # cannot be correlated across tenant scopes from public artifacts.
    return _hmac_subject(key, "account-subject", tenant_id, account_id)


def _private_content_binding_hmac(
    key: bytes,
    *,
    attestation_sha256: str,
    actor_tenant_id: str,
    actor_account_id: str,
    pseudonym_key_id: str,
) -> str:
    facts = {
        "attestation_sha256": attestation_sha256,
        "actor_tenant_id": actor_tenant_id,
        "actor_account_id": actor_account_id,
        "pseudonym_key_id": pseudonym_key_id,
    }
    # The digest is over the complete canonical public attestation, including
    # every actor field and the exact ordered supporting-attestation graph.
    message = b"cas-harness-human-attestation/v2/private-content-binding\0" + (
        _canonical_json_bytes(facts)
    )
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def _decode_pseudonym_key_secret(value: str) -> bytes:
    if not value.startswith(_KEY_SECRET_PREFIX):
        raise ValueError(
            "human attestation pseudonym keys require canonical base64url encoding"
        )
    payload = value.removeprefix(_KEY_SECRET_PREFIX)
    if not payload or "=" in payload or re.fullmatch(r"[A-Za-z0-9_-]+", payload) is None:
        raise ValueError(
            "human attestation pseudonym keys require canonical base64url encoding"
        )
    padding = "=" * ((4 - len(payload) % 4) % 4)
    try:
        decoded = base64.b64decode(
            payload + padding,
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "human attestation pseudonym keys require canonical base64url encoding"
        ) from exc
    _validate_pseudonym_key_material(decoded)
    if _encode_pseudonym_key_secret(decoded) != value:
        raise ValueError(
            "human attestation pseudonym keys require canonical base64url encoding"
        )
    return decoded


def _encode_pseudonym_key_secret(key: bytes) -> str:
    encoded = base64.urlsafe_b64encode(key).rstrip(b"=").decode("ascii")
    return _KEY_SECRET_PREFIX + encoded


def _validate_pseudonym_key_material(key: bytes) -> None:
    if not isinstance(key, bytes) or not (
        _MIN_PSEUDONYM_KEY_BYTES <= len(key) <= _MAX_PSEUDONYM_KEY_BYTES
    ):
        raise ValueError(
            "human attestation pseudonym keys require 32 to 64 random bytes"
        )
    # Randomness cannot be proven after generation, but predictable placeholders
    # can and must be rejected. These checks reject repeated blocks, arithmetic
    # sequences, low-diversity buffers, and human-readable passphrases while
    # retaining overwhelming acceptance probability for CSPRNG output.
    if len(set(key)) < 16:
        raise ValueError(
            "human attestation pseudonym keys must be independently random"
        )
    if sum(byte < 0x20 or byte > 0x7E for byte in key) < 4:
        raise ValueError(
            "human attestation pseudonym keys must be independently random"
        )
    if any(
        len(key) % period == 0
        and key == key[:period] * (len(key) // period)
        for period in range(1, (len(key) // 2) + 1)
    ):
        raise ValueError(
            "human attestation pseudonym keys must be independently random"
        )
    if len(key) > 2 and len(
        {(right - left) % 256 for left, right in zip(key, key[1:], strict=False)}
    ) == 1:
        raise ValueError(
            "human attestation pseudonym keys must be independently random"
        )


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def canonical_evidence_binding_sha256(
    gate: str, evidence: Mapping[str, Any]
) -> str:
    """Hash the exact non-circular evidence facts a human attests to."""

    common = {
        "gate": gate,
        "environment": evidence.get("environment"),
        "repository": evidence.get("repository"),
        "master_head_sha": evidence.get("master_head_sha"),
        "deploy_id": evidence.get("deploy_id"),
        "human_assurance_boundary": evidence.get("human_assurance_boundary"),
    }
    if gate == "legal_publication_approval":
        bound = {
            **common,
            "documents": evidence.get("documents"),
            "claim_status_vocabulary": evidence.get("claim_status_vocabulary"),
        }
    elif gate == "claim_honesty":
        bound = {
            **common,
            "artifact_sha256": evidence.get("artifact_sha256"),
            "machine_subject": evidence.get("machine_subject"),
            "machine_subject_sha256": evidence.get("machine_subject_sha256"),
            "boundaries": evidence.get("boundaries"),
            "claim_status_vocabulary": evidence.get("claim_status_vocabulary"),
        }
    elif gate == "incident_tabletop":
        incident = dict(evidence.get("incident") or {})
        tabletop = dict(evidence.get("tabletop") or {})
        incident.pop("postmortem_uri", None)
        incident.pop("postmortem_sha256", None)
        tabletop.pop("evidence_uri", None)
        tabletop.pop("evidence_sha256", None)
        bound = {**common, "incident": incident, "tabletop": tabletop}
    elif gate == "release_decision":
        bound = {
            **common,
            "status": evidence.get("status"),
            "approved_at_utc": evidence.get("approved_at_utc"),
            "approver_roles": evidence.get("approver_roles"),
        }
    else:
        raise HumanAttestationInvalid("gate has no human-attestation binding")
    return hashlib.sha256(_canonical_json_bytes(bound)).hexdigest()


def _utc_now(value: datetime | None = None) -> datetime:
    stamp = value or datetime.now(UTC)
    if stamp.tzinfo is None:
        raise HumanAttestationInvalid("timestamp must be timezone-aware")
    return stamp.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise HumanAttestationUnavailable("attestation timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise HumanAttestationUnavailable("attestation timestamp is invalid") from exc
    if _format_utc(parsed) != value:
        raise HumanAttestationUnavailable("attestation timestamp is not canonical")
    return parsed


__all__ = [
    "HumanAttestation",
    "HumanAttestationError",
    "HumanAttestationInvalid",
    "HumanAttestationNotFound",
    "HumanAttestationStore",
    "HumanAttestationUnavailable",
    "PUBLIC_HUMAN_ASSURANCE_BOUNDARY",
    "PUBLIC_PATH_PATTERN",
    "canonical_evidence_binding_sha256",
    "human_attestation_url",
    "human_attestation_pseudonym_key_matches_secret",
    "parse_human_attestation_pseudonym_keyring",
]
