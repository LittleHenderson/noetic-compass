"""Dedicated keyed pseudonyms for public customer-production artifacts.

This key domain is intentionally separate from human-attestation actor
pseudonyms and every authentication, provider, signing, and billing secret.
Public subjects are deterministic only within one explicit tenant scope,
identifier domain, and key ID.  Retaining historical keys lets immutable
artifacts remain verifiable across rotation without rewriting their bytes.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
import hashlib
import hmac
import json
import re
from types import MappingProxyType
from typing import Any


PSEUDONYMIZATION_SCHEME = "hmac-sha256-tenant-scoped-v1"
KEY_SECRET_PREFIX = "base64url:"
KEY_ID_PATTERN = re.compile(r"^cpk_[0-9a-f]{32}$")
SUBJECT_PATTERN = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")
MIN_KEY_BYTES = 32
MAX_KEY_BYTES = 64

TENANT_DOMAIN = "tenant"
ACCOUNT_DOMAIN = "account"
PUBLICATION_TENANT_DOMAIN = "publication-tenant"
PUBLICATION_ACCOUNT_DOMAIN = "publication-account"
PUBLICATION_CONTENT_BINDING_DOMAIN = "publication-content-binding"
BILLING_CUSTOMER_DOMAIN = "billing-provider-customer"
BILLING_SUBSCRIPTION_DOMAIN = "billing-provider-subscription"
BILLING_INVOICE_DOMAIN = "billing-provider-invoice"
ACCOUNTS_BILLING_CONTENT_BINDING_DOMAIN = "accounts-billing-content-binding"
SUPPORT_TICKET_DOMAIN = "support-ticket"
CRM_LEAD_DOMAIN = "crm-lead"
AIRTABLE_RECORD_DOMAIN = "airtable-record"
ALERT_ACKNOWLEDGEMENT_ACTOR_DOMAIN = "alert-acknowledgement-actor"
HOSTED_JOURNEY_CONTENT_BINDING_DOMAIN = "hosted-journey-content-binding"
SUPPORT_CRM_CONTENT_BINDING_DOMAIN = "support-crm-content-binding"
HOSTED_JOURNEY_TRACE_DOMAIN = "hosted-journey-trace"
SUPPORT_CRM_REQUEST_TRACE_DOMAIN = "support-crm-request-trace"
SUPPORT_PUBLIC_INTAKE_CONTENT_BINDING_DOMAIN = (
    "support-public-intake-content-binding"
)

ALLOWED_DOMAINS = frozenset(
    {
        TENANT_DOMAIN,
        ACCOUNT_DOMAIN,
        PUBLICATION_TENANT_DOMAIN,
        PUBLICATION_ACCOUNT_DOMAIN,
        PUBLICATION_CONTENT_BINDING_DOMAIN,
        BILLING_CUSTOMER_DOMAIN,
        BILLING_SUBSCRIPTION_DOMAIN,
        BILLING_INVOICE_DOMAIN,
        ACCOUNTS_BILLING_CONTENT_BINDING_DOMAIN,
        SUPPORT_TICKET_DOMAIN,
        CRM_LEAD_DOMAIN,
        AIRTABLE_RECORD_DOMAIN,
        ALERT_ACKNOWLEDGEMENT_ACTOR_DOMAIN,
        HOSTED_JOURNEY_CONTENT_BINDING_DOMAIN,
        SUPPORT_CRM_CONTENT_BINDING_DOMAIN,
        HOSTED_JOURNEY_TRACE_DOMAIN,
        SUPPORT_CRM_REQUEST_TRACE_DOMAIN,
        SUPPORT_PUBLIC_INTAKE_CONTENT_BINDING_DOMAIN,
    }
)


def parse_customer_production_pseudonym_keyring(
    raw_json: str, *, active_key_id: str
) -> Mapping[str, bytes]:
    """Parse the strict rotation-aware customer-production keyring.

    Values are canonical unpadded base64url encodings of 32--64 random bytes.
    IDs are opaque 128-bit labels and carry no tenant, actor, date, or role.
    """

    if not isinstance(raw_json, str) or not raw_json:
        raise ValueError("customer-production pseudonym keyring is required")
    if KEY_ID_PATTERN.fullmatch(active_key_id or "") is None:
        raise ValueError("customer-production active pseudonym key id is invalid")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(
                    "customer-production pseudonym keyring has duplicate keys"
                )
            result[key] = value
        return result

    try:
        decoded = json.loads(raw_json, object_pairs_hook=reject_duplicates)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("customer-production pseudonym keyring is invalid") from exc
    if not isinstance(decoded, dict) or not (1 <= len(decoded) <= 16):
        raise ValueError("customer-production pseudonym keyring is invalid")

    parsed: dict[str, bytes] = {}
    seen: set[bytes] = set()
    for key_id, encoded in decoded.items():
        if (
            not isinstance(key_id, str)
            or KEY_ID_PATTERN.fullmatch(key_id) is None
            or not isinstance(encoded, str)
        ):
            raise ValueError("customer-production pseudonym keyring is invalid")
        key = _decode_key(encoded)
        if key in seen:
            raise ValueError("customer-production pseudonym keyring is invalid")
        parsed[key_id] = key
        seen.add(key)
    if active_key_id not in parsed:
        raise ValueError("customer-production active pseudonym key is unavailable")
    return MappingProxyType(parsed)


def customer_production_pseudonym_key_matches_secret(
    key: bytes, candidate: str
) -> bool:
    """Compare key material to another configured secret without exposing it."""

    _validate_key_material(key)
    if not isinstance(candidate, str) or not candidate:
        return False
    external = _encode_key(key)
    payload = external.removeprefix(KEY_SECRET_PREFIX)
    candidate_bytes = candidate.encode("utf-8")
    return any(
        hmac.compare_digest(candidate_bytes, value)
        for value in (key, external.encode("ascii"), payload.encode("ascii"))
    )


class CustomerProductionPseudonymizer:
    """Derive and verify exact public subjects under retained rotation keys."""

    def __init__(
        self, keyring: Mapping[str, bytes], *, active_key_id: str
    ) -> None:
        if KEY_ID_PATTERN.fullmatch(active_key_id or "") is None:
            raise ValueError("active customer-production pseudonym key id is invalid")
        if not isinstance(keyring, Mapping) or not (1 <= len(keyring) <= 16):
            raise ValueError("customer-production pseudonym keyring is invalid")
        keys: dict[str, bytes] = {}
        seen: set[bytes] = set()
        for key_id, key in keyring.items():
            if (
                not isinstance(key_id, str)
                or KEY_ID_PATTERN.fullmatch(key_id) is None
                or not isinstance(key, bytes)
                or key in seen
            ):
                raise ValueError("customer-production pseudonym keyring is invalid")
            _validate_key_material(key)
            keys[key_id] = key
            seen.add(key)
        if active_key_id not in keys:
            raise ValueError("active customer-production pseudonym key is unavailable")
        self._keys = MappingProxyType(keys)
        self._active_key_id = active_key_id

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    @property
    def scheme(self) -> str:
        return PSEUDONYMIZATION_SCHEME

    @property
    def key_ids(self) -> frozenset[str]:
        return frozenset(self._keys)

    def metadata(self, *, key_id: str | None = None) -> dict[str, str]:
        selected = self._selected_key_id(key_id)
        return {
            "pseudonymization_scheme": PSEUDONYMIZATION_SCHEME,
            "pseudonym_key_id": selected,
        }

    def subject(
        self,
        *,
        domain: str,
        tenant_scope: str,
        value: str,
        key_id: str | None = None,
    ) -> str:
        selected = self._selected_key_id(key_id)
        if domain not in ALLOWED_DOMAINS:
            raise ValueError("customer-production pseudonym domain is invalid")
        if not isinstance(tenant_scope, str) or not tenant_scope:
            raise ValueError("customer-production pseudonym tenant scope is required")
        if not isinstance(value, str) or not value:
            raise ValueError("customer-production pseudonym source value is required")
        if any("\x00" in item for item in (tenant_scope, value)):
            raise ValueError("customer-production pseudonym input is invalid")
        message = (
            "cas-harness-customer-production-pseudonym/v1\0"
            + domain
            + "\0"
            + tenant_scope
            + "\0"
            + value
        ).encode("utf-8")
        return "hmac-sha256:" + hmac.new(
            self._keys[selected], message, hashlib.sha256
        ).hexdigest()

    def assert_subject(
        self,
        subject: object,
        *,
        domain: str,
        tenant_scope: str,
        value: str,
        key_id: str,
    ) -> str:
        if not isinstance(subject, str) or SUBJECT_PATTERN.fullmatch(subject) is None:
            raise ValueError("customer-production pseudonym subject is invalid")
        expected = self.subject(
            domain=domain,
            tenant_scope=tenant_scope,
            value=value,
            key_id=key_id,
        )
        if not hmac.compare_digest(subject, expected):
            raise ValueError("customer-production pseudonym subject does not match")
        return subject

    def _selected_key_id(self, value: str | None) -> str:
        selected = self._active_key_id if value is None else value
        if not isinstance(selected, str) or selected not in self._keys:
            raise ValueError("customer-production pseudonym key is unavailable")
        return selected


def validate_public_pseudonym_metadata(
    value: Mapping[str, Any], *, available_key_ids: frozenset[str] | None = None
) -> str:
    """Validate exact public scheme/key metadata and return its key ID."""

    if value.get("pseudonymization_scheme") != PSEUDONYMIZATION_SCHEME:
        raise ValueError("customer-production pseudonymization scheme is invalid")
    key_id = value.get("pseudonym_key_id")
    if not isinstance(key_id, str) or KEY_ID_PATTERN.fullmatch(key_id) is None:
        raise ValueError("customer-production pseudonym key id is invalid")
    if available_key_ids is not None and key_id not in available_key_ids:
        raise ValueError("customer-production pseudonym verification key is unavailable")
    return key_id


def validate_public_pseudonym_subject(value: object) -> str:
    if not isinstance(value, str) or SUBJECT_PATTERN.fullmatch(value) is None:
        raise ValueError("customer-production pseudonym subject is invalid")
    return value


def _decode_key(value: str) -> bytes:
    if not value.startswith(KEY_SECRET_PREFIX):
        raise ValueError(
            "customer-production pseudonym keys require canonical base64url encoding"
        )
    payload = value.removeprefix(KEY_SECRET_PREFIX)
    if not payload or "=" in payload or re.fullmatch(r"[A-Za-z0-9_-]+", payload) is None:
        raise ValueError(
            "customer-production pseudonym keys require canonical base64url encoding"
        )
    padding = "=" * ((4 - len(payload) % 4) % 4)
    try:
        decoded = base64.b64decode(
            payload + padding, altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "customer-production pseudonym keys require canonical base64url encoding"
        ) from exc
    _validate_key_material(decoded)
    if _encode_key(decoded) != value:
        raise ValueError(
            "customer-production pseudonym keys require canonical base64url encoding"
        )
    return decoded


def _encode_key(key: bytes) -> str:
    return KEY_SECRET_PREFIX + base64.urlsafe_b64encode(key).rstrip(b"=").decode(
        "ascii"
    )


def _validate_key_material(key: bytes) -> None:
    if not isinstance(key, bytes) or not (MIN_KEY_BYTES <= len(key) <= MAX_KEY_BYTES):
        raise ValueError(
            "customer-production pseudonym keys require 32 to 64 random bytes"
        )
    if len(set(key)) < 16:
        raise ValueError(
            "customer-production pseudonym keys must be independently random"
        )
    if sum(byte < 0x20 or byte > 0x7E for byte in key) < 4:
        raise ValueError(
            "customer-production pseudonym keys must be independently random"
        )
    if any(
        len(key) % period == 0
        and key == key[:period] * (len(key) // period)
        for period in range(1, (len(key) // 2) + 1)
    ):
        raise ValueError(
            "customer-production pseudonym keys must be independently random"
        )
    if len(key) > 2 and len(
        {(right - left) % 256 for left, right in zip(key, key[1:], strict=False)}
    ) == 1:
        raise ValueError(
            "customer-production pseudonym keys must be independently random"
        )


__all__ = [
    "ACCOUNT_DOMAIN",
    "ACCOUNTS_BILLING_CONTENT_BINDING_DOMAIN",
    "AIRTABLE_RECORD_DOMAIN",
    "ALERT_ACKNOWLEDGEMENT_ACTOR_DOMAIN",
    "BILLING_CUSTOMER_DOMAIN",
    "BILLING_INVOICE_DOMAIN",
    "BILLING_SUBSCRIPTION_DOMAIN",
    "CRM_LEAD_DOMAIN",
    "CustomerProductionPseudonymizer",
    "HOSTED_JOURNEY_CONTENT_BINDING_DOMAIN",
    "HOSTED_JOURNEY_TRACE_DOMAIN",
    "KEY_ID_PATTERN",
    "PSEUDONYMIZATION_SCHEME",
    "PUBLICATION_ACCOUNT_DOMAIN",
    "PUBLICATION_CONTENT_BINDING_DOMAIN",
    "PUBLICATION_TENANT_DOMAIN",
    "SUBJECT_PATTERN",
    "SUPPORT_TICKET_DOMAIN",
    "SUPPORT_CRM_CONTENT_BINDING_DOMAIN",
    "SUPPORT_CRM_REQUEST_TRACE_DOMAIN",
    "SUPPORT_PUBLIC_INTAKE_CONTENT_BINDING_DOMAIN",
    "TENANT_DOMAIN",
    "customer_production_pseudonym_key_matches_secret",
    "parse_customer_production_pseudonym_keyring",
    "validate_public_pseudonym_metadata",
    "validate_public_pseudonym_subject",
]
