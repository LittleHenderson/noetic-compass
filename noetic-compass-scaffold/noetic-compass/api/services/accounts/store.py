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
from dataclasses import replace
from datetime import UTC, datetime
from typing import Callable, Optional

from api.services.crm.models import normalize_email
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

from .invites import generate_invite_code, is_redeemable
from .credentials import (
    CREDENTIAL_VERSION,
    LEGACY_CREDENTIAL_VERSION,
    SUPPORTED_CREDENTIAL_VERSIONS,
    credential_matches,
    hash_account_credential,
    validate_account_credential,
    validate_credential_pepper,
)
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

    def tenant_has_account(self, tenant_id: str, *, active_only: bool = True) -> bool:
        """Return whether the durable account domain contains this tenant.

        Platform-only provisioning/billing routes use this to refuse grants for a typo or a
        fabricated tenant id. The fixed account-storage partition is scanned server-side; no
        account/customer endpoint exposes this enumeration.
        """
        normalized = tenant_id.strip()
        if not normalized:
            return False
        for record in self._store.list(self._tenant, ACCOUNT_KIND):
            account = Account.from_payload(record.payload)
            if account.tenant_id == normalized and (account.is_active or not active_only):
                return True
        return False

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
        account_id = str(index.payload.get("account_id") or "") if index is not None else ""
        # Always perform the second keyed read. Unknown and known identities therefore have the
        # same storage-call shape before the constant-time credential digest comparison.
        record = self._store.get(
            self._tenant, ACCOUNT_KIND, account_id or "acct-auth-dummy"
        )
        if not account_id or record is None:
            return None
        return Account.from_payload(record.payload)

    def authenticate_account(
        self, email_or_username: str, api_credential: str | None
    ) -> Optional[Account]:
        """Resolve and verify one account without exposing which check failed.

        credential_matches performs a constant-time digest comparison even when the identity is
        unknown or the stored record predates per-account credentials.
        """
        account = self.get_account_by_email(email_or_username)
        if not credential_matches(
            account, api_credential, pepper=self._credential_pepper
        ):
            return None
        if account is None or not account.is_active:
            return None
        if account.credential_version == LEGACY_CREDENTIAL_VERSION:
            account = self._upgrade_legacy_credential(account, api_credential or "")
        return account

    def _upgrade_legacy_credential(
        self, account: Account, presented: str
    ) -> Account:
        """CAS-upgrade a verified v1 digest to the pepper-keyed v2 format."""
        for _ in range(12):
            record = self._store.get(self._tenant, ACCOUNT_KIND, account.account_id)
            if record is None:
                raise RuntimeError("legacy credential account disappeared during upgrade")
            current = Account.from_payload(record.payload)
            if current.credential_version == CREDENTIAL_VERSION:
                if not credential_matches(
                    current, presented, pepper=self._credential_pepper
                ):
                    raise RuntimeError("credential changed during legacy upgrade")
                return current
            if (
                current.credential_version != LEGACY_CREDENTIAL_VERSION
                or not credential_matches(
                    current, presented, pepper=self._credential_pepper
                )
            ):
                raise RuntimeError("legacy credential changed during upgrade")
            now = datetime.now(UTC).isoformat()
            upgraded = replace(
                current,
                credential_hash=hash_account_credential(
                    presented, pepper=self._credential_pepper
                ),
                credential_version=CREDENTIAL_VERSION,
                credential_issued_at=now,
                auth_epoch=current.auth_epoch + 1,
                updated_at=now,
            )
            try:
                self._store.put(
                    record.with_payload(upgraded.to_payload()),
                    expected_version=record.version,
                )
                return upgraded
            except VersionConflict:
                continue
        raise RuntimeError("legacy credential upgrade contention did not converge")

    def has_accounts(self) -> bool:
        return bool(self._store.list(self._tenant, ACCOUNT_KIND))

    def has_active_owner(self, *, tenant_id: str) -> bool:
        """Return whether one granted tenant has an active administrative owner.

        Account records share one internal storage tenant, so an unscoped scan would let a
        platform-provisioned synthetic tenant satisfy (or block) the permanent first-owner
        bootstrap.  Callers must name the granted tenant whose owner authority they mean.
        """
        tenant = tenant_id.strip()
        if not tenant:
            return False
        return any(
            (account := Account.from_payload(record.payload)).role == "owner"
            and account.is_active
            and bool(account.credential_hash)
            and account.credential_version in SUPPORTED_CREDENTIAL_VERSIONS
            and account.tenant_id == tenant
            for record in self._store.list(self._tenant, ACCOUNT_KIND)
        )

    def bootstrap_owner(
        self,
        *,
        email_or_username: str,
        tenant_id: str,
        api_credential: str,
        display_name: Optional[str] = None,
    ) -> Account:
        from .bootstrap import bootstrap_first_owner

        return bootstrap_first_owner(
            self,
            email_or_username=email_or_username,
            tenant_id=tenant_id,
            api_credential=api_credential,
            display_name=display_name,
        )

    def recover_bootstrap_owner(
        self,
        *,
        email_or_username: str,
        tenant_id: str,
        new_credential: str,
    ) -> Account:
        from .bootstrap import recover_bootstrap_owner

        return recover_bootstrap_owner(
            self,
            email_or_username=email_or_username,
            tenant_id=tenant_id,
            new_credential=new_credential,
        )

    def rotate_account_credential(
        self, account_id: str, *, new_credential: str
    ) -> Optional[Account]:
        """Atomically hash a client-held retry-safe replacement credential."""
        validate_account_credential(new_credential)
        for _ in range(12):
            record = self._store.get(self._tenant, ACCOUNT_KIND, account_id)
            if record is None:
                return None
            account = Account.from_payload(record.payload)
            now = datetime.now(UTC).isoformat()
            updated = replace(
                account,
                credential_hash=hash_account_credential(
                    new_credential, pepper=self._credential_pepper
                ),
                credential_version=CREDENTIAL_VERSION,
                credential_issued_at=now,
                auth_epoch=account.auth_epoch + 1,
                updated_at=now,
            )
            try:
                self._store.put(
                    record.with_payload(updated.to_payload()),
                    expected_version=record.version,
                )
            except VersionConflict:
                continue
            return updated
        raise RuntimeError("credential rotation contention did not converge")

    # --- the security-critical redeem -------------------------------------

    def redeem_invite(
        self,
        *,
        code: str,
        email_or_username: str,
        api_credential: str,
        display_name: Optional[str] = None,
    ) -> Account:
        """Crash-safe redemption: reserve the use before making an account visible."""
        from .redemption import redeem_invite_crash_safe

        return redeem_invite_crash_safe(
            self,
            code=code,
            email_or_username=email_or_username,
            api_credential=api_credential,
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
