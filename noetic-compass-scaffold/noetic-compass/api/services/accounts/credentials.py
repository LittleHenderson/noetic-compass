"""Per-account API credential generation and constant-time verification.

Credentials are high-entropy opaque bearer values. The durable account record stores only a
domain-separated SHA-256 digest. A random persisted nonce plus a server-only deployment pepper
lets an interrupted invite/bootstrap state machine derive the same credential during recovery
without storing the bearer value itself.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Optional, Protocol


CREDENTIAL_VERSION = "cas-account-api-key.v1"
CREDENTIAL_PREFIX = "casak_"
MIN_PEPPER_LENGTH = 32
_DUMMY_HASH = hashlib.sha256(b"cas-account-api-key.v1:invalid").hexdigest()


class CredentialAccount(Protocol):
    credential_hash: Optional[str]


def validate_credential_pepper(pepper: str) -> str:
    value = (pepper or "").strip()
    if len(value) < MIN_PEPPER_LENGTH:
        raise RuntimeError(
            "NC_ACCOUNT_CREDENTIAL_PEPPER must contain at least 32 characters when accounts are enabled"
        )
    return value


def new_credential_nonce() -> str:
    """Return 256 bits of CSPRNG entropy for one account credential."""
    return secrets.token_urlsafe(32)


def derive_account_credential(*, pepper: str, nonce: str) -> str:
    """Derive the opaque credential from a server secret and a non-secret random nonce."""
    key = validate_credential_pepper(pepper).encode("utf-8")
    digest = hmac.new(
        key,
        f"{CREDENTIAL_VERSION}:{nonce}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{CREDENTIAL_PREFIX}{encoded}"


def hash_account_credential(credential: str) -> str:
    value = credential or ""
    return hashlib.sha256(
        f"{CREDENTIAL_VERSION}:{value}".encode("utf-8")
    ).hexdigest()


def credential_matches(account: CredentialAccount | None, presented: str | None) -> bool:
    """Compare in constant time even for unknown accounts or legacy records with no credential."""
    expected = account.credential_hash if account and account.credential_hash else _DUMMY_HASH
    candidate = hash_account_credential(presented or "")
    matched = hmac.compare_digest(expected.encode("ascii"), candidate.encode("ascii"))
    return bool(account and account.credential_hash and matched)
