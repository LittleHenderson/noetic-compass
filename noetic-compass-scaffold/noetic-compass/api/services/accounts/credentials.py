"""Validation, one-way hashing, and constant-time verification for account credentials.

The client generates and retains a high-entropy opaque bearer value. Durable records keep only a
domain-separated HMAC digest keyed by the deployment pepper; no nonce or recoverable bearer value
is persisted. Retry-safe workflows verify the same client-held credential against that digest.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Optional, Protocol


LEGACY_CREDENTIAL_VERSION = "cas-account-api-key.v1"
CREDENTIAL_VERSION = "cas-account-api-key.v2"
SUPPORTED_CREDENTIAL_VERSIONS = frozenset(
    {LEGACY_CREDENTIAL_VERSION, CREDENTIAL_VERSION}
)
CREDENTIAL_PREFIX = "casak_"
_CREDENTIAL_PATTERN = re.compile(r"^casak_[A-Za-z0-9_-]{43,128}$")


def validate_account_credential(raw: str) -> str:
    """Require the generated-key shape and reject obvious low-entropy placeholders."""
    if not _CREDENTIAL_PATTERN.fullmatch(raw) or len(set(raw.removeprefix(CREDENTIAL_PREFIX))) < 12:
        raise ValueError("account credential must be a high-entropy casak_ generated key")
    return raw


MIN_PEPPER_LENGTH = 32
_DUMMY_HASH = hashlib.sha256(b"cas-account-api-key.v1:invalid").hexdigest()


class CredentialAccount(Protocol):
    credential_hash: Optional[str]
    credential_version: Optional[str]


def validate_credential_pepper(pepper: str) -> str:
    value = (pepper or "").strip()
    if len(value) < MIN_PEPPER_LENGTH:
        raise RuntimeError(
            "NC_ACCOUNT_CREDENTIAL_PEPPER must contain at least 32 characters when accounts are enabled"
        )
    return value


def hash_account_credential(credential: str, *, pepper: str) -> str:
    key = validate_credential_pepper(pepper).encode("utf-8")
    value = credential or ""
    return hmac.new(
        key,
        f"{CREDENTIAL_VERSION}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def legacy_hash_account_credential(credential: str) -> str:
    """Reproduce the short-lived v1 unpeppered digest for one-time login migration."""
    return hashlib.sha256(
        f"{LEGACY_CREDENTIAL_VERSION}:{credential or ''}".encode("utf-8")
    ).hexdigest()


def credential_matches(
    account: CredentialAccount | None,
    presented: str | None,
    *,
    pepper: str,
) -> bool:
    """Compare in constant time even for unknown accounts or legacy records with no credential."""
    expected = account.credential_hash if account and account.credential_hash else _DUMMY_HASH
    v2_candidate = hash_account_credential(presented or "", pepper=pepper)
    v1_candidate = legacy_hash_account_credential(presented or "")
    v2_match = hmac.compare_digest(expected.encode("ascii"), v2_candidate.encode("ascii"))
    v1_match = hmac.compare_digest(expected.encode("ascii"), v1_candidate.encode("ascii"))
    if not account or not account.credential_hash:
        return False
    if account.credential_version == LEGACY_CREDENTIAL_VERSION:
        return v1_match
    return account.credential_version == CREDENTIAL_VERSION and v2_match
