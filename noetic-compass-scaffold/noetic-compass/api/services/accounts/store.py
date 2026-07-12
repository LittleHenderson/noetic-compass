"""Durable account, invitation, and credential storage over the shared StateStore.

Invitation redemption is a forward-only state machine. It first reserves one use in the
version-checked invite record, then idempotently creates the unique email index and account.
A process crash at any write boundary is repaired by retrying the same code and identity; no
rollback window can expose an account before its invite use is counted.

All account-domain records use one internal storage tenant so an invitation can be resolved by
code alone. The granted tenant remains a server-derived account payload field. Account records
persist credential hashes only; raw account credentials exist solely in the redemption response.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Optional

from api.services.crm.models import normalize_email
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

from .invites import generate_invite_code, is_redeemable
from .credentials import credential_matches, validate_credential_pepper
from .models import (
    ACCOUNT_EMAIL_INDEX_KIND,
    ACCOUNT_KIND,
    DEFAULT_INVITE_ROLE,
    INVITE_KIND,
    Account,
    InviteCode,
    Role,
    invite_code_hash,
    normalize_role,
)

# The single storage tenant all account-domain records live under (see module docstring). This is
# the ledger storage key, NOT the tenant an account is granted -- that granted tenant is a payload
# fact carried into token claims. Per-customer storage partitioning is a later PR.
ACCOUNTS_STORAGE_TENANT = "accounts"
# The tenant a redeemed account is granted by default, when an invite does not pin one. Distinct
# from the storage tenant on purpose; both happen to share the same literal today.
DEFAULT_GRANTED_TENANT = "accounts"

# Record-id prefixes (kept human-greppable, mirroring the substrate's ``new_record_id`` style).
_ACCOUNT_ID_PREFIX = "acct"
_INVITE_ID_PREFIX = "invite"


class InviteRedemptionError(Exception):
    """A redeem attempt was refused. ``reason`` is a short, client-safe code.

    Carries no detail that would help an attacker distinguish "code does not exist" from "code is
    used/expired" beyond the coarse reason -- the route maps every reason to the same 4xx shape so
    redemption stays fail-closed and non-enumerable.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class AccountStore:
    """Durable account/invite store over a single :class:`StateStore` backend."""

    def __init__(
        self,
        store: StateStore,
        *,
        credential_pepper: str,
        storage_tenant: str = ACCOUNTS_STORAGE_TENANT,
        failure_injector: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._store = store
        # The single ledger tenant every account-domain record is keyed under.
        self._tenant = storage_tenant
        self._credential_pepper = validate_credential_pepper(credential_pepper)
        self._failure_injector = failure_injector

    # --- invites -----------------------------------------------------------

    def create_invite(
        self,
        *,
        role: Role = DEFAULT_INVITE_ROLE,
        target_email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        expires_at: Optional[str] = None,
        max_uses: int = 1,
        code: Optional[str] = None,
        source: str = "accounts.create_invite",
    ) -> InviteCode:
        """Mint and persist a new invite.

        The code is cryptographically random unless one is supplied (tests may pin a code).
        ``role`` and ``tenant_id`` are baked in here and become the SERVER-SIDE facts a redeemed
        account inherits (its granted tenant + role). The invite RECORD is stored under the fixed
        storage tenant so it is resolvable by code alone.
        """
        if max_uses < 1:
            raise ValueError("max_uses must be >= 1")
        role = normalize_role(role)
        granted_tenant = (tenant_id or DEFAULT_GRANTED_TENANT).strip() or DEFAULT_GRANTED_TENANT
        raw_code = code or generate_invite_code()
        invite = InviteCode(
            code=raw_code,
            code_hash=invite_code_hash(raw_code),
            role=role,
            tenant_id=granted_tenant,
            target_email=normalize_email(target_email) if target_email else None,
            expires_at=expires_at,
            max_uses=max_uses,
            uses=0,
        )
        record_id = _invite_record_id(invite.code)
        record = LedgerRecord.new(
            tenant_id=self._tenant,
            kind=INVITE_KIND,
            record_id=record_id,
            payload=invite.to_payload(),
            source=source,
            trace_id=record_id,
        )
        # expected_version=0 -> create. A duplicate code (astronomically unlikely for a random
        # code; possible only if a caller pins one) raises VersionConflict, which we surface.
        self._store.put(record, expected_version=0)
        return invite

    def get_invite(self, code: str) -> Optional[InviteCode]:
        """Look up an invite by code. Returns ``None`` for an absent code (fail closed)."""
        record = self._read_invite_record(code)
        if record is None:
            return None
        return InviteCode.from_payload(record.payload)

    # --- accounts ----------------------------------------------------------

    def get_account_by_id(self, account_id: str) -> Optional[Account]:
        record = self._store.get(self._tenant, ACCOUNT_KIND, account_id)
        if record is None:
            return None
        return Account.from_payload(record.payload)

    def get_account_by_email(self, email_or_username: str) -> Optional[Account]:
        """Resolve the account for a login identity via the email-index record.

        This is the lookup the identity-login branch in ``auth.py`` uses: given the supplied
        username/email, find the durable account whose SERVER-DERIVED claims the token will carry.
        Returns ``None`` for an unknown identity (fail closed -- an unknown user has no account).
        """
        normalized = normalize_email(email_or_username)
        if not normalized:
            return None
        index = self._store.get(self._tenant, ACCOUNT_EMAIL_INDEX_KIND, _email_index_id(normalized))
        if index is None:
            return None
        account_id = str(index.payload.get("account_id") or "")
        if not account_id:
            return None
        return self.get_account_by_id(account_id)

    def authenticate_account(
        self, email_or_username: str, api_credential: str | None
    ) -> Optional[Account]:
        """Resolve and verify one account without exposing which check failed.

        credential_matches performs a constant-time digest comparison even when the identity is
        unknown or the stored record predates per-account credentials.
        """
        account = self.get_account_by_email(email_or_username)
        if not credential_matches(account, api_credential):
            return None
        if account is None or not account.is_active:
            return None
        return account

    # --- the security-critical redeem -------------------------------------

    def redeem_invite(
        self,
        *,
        code: str,
        email_or_username: str,
        display_name: Optional[str] = None,
    ) -> Account:
        """Crash-safe redemption: reserve the use before making an account visible."""
        from .redemption import redeem_invite_crash_safe

        return redeem_invite_crash_safe(
            self,
            code=code,
            email_or_username=email_or_username,
            display_name=display_name,
        )

    # --- helpers -----------------------------------------------------------

    def _fail_after(self, boundary: str) -> None:
        """Deterministic crash hook used by boundary-recovery tests."""
        if self._failure_injector is not None:
            self._failure_injector(boundary)

    def _read_invite_record(self, code: str) -> Optional[LedgerRecord]:
        """Read the raw invite ledger record (so callers also get its version).

        Invites live under the single storage tenant, so a code resolves without a tenant hint --
        which is essential: the redeemer presents only a code.
        """
        return self._store.get(self._tenant, INVITE_KIND, _invite_record_id(code))

    def _claim_email(self, normalized_email: str, *, account_id: str) -> None:
        """Write the email-uniqueness index at version 0.

        Raises :class:`InviteRedemptionError` ``email_taken`` when the email is already claimed by
        a DIFFERENT account. A pre-existing index pointing at THIS same ``account_id`` is an
        idempotent re-entry (a concurrent redeem of the same code+email) and is accepted silently.
        """
        index_id = _email_index_id(normalized_email)
        index_record = LedgerRecord.new(
            tenant_id=self._tenant,
            kind=ACCOUNT_EMAIL_INDEX_KIND,
            record_id=index_id,
            payload={"email": normalized_email, "account_id": account_id},
            parent_ids=(account_id,),
            source="accounts.email_index",
            trace_id=account_id,
        )
        try:
            self._store.put(index_record, expected_version=0)
        except VersionConflict as exc:
            current = self._store.get(self._tenant, ACCOUNT_EMAIL_INDEX_KIND, index_id)
            if current is not None and str(current.payload.get("account_id") or "") == account_id:
                # Same account already holds this email -> idempotent, not a collision.
                return
            raise InviteRedemptionError("email_taken") from exc

def _invite_record_id(code: str) -> str:
    """Deterministic record-id for an invite, derived from a digest of its code.

    The code itself is the secret; the record-id is a non-secret digest so the code is not stored
    in the id slot in the clear while remaining a stable lookup key.
    """
    digest = invite_code_hash(code)[:32]
    return f"{_INVITE_ID_PREFIX}-{digest}"


def _email_index_id(normalized_email: str) -> str:
    digest = hashlib.sha256(f"email:{normalized_email}".encode("utf-8")).hexdigest()[:32]
    return f"acctemail-{digest}"
