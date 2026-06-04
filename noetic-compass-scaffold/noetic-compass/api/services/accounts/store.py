"""Durable Account + InviteCode storage over the ``StateStore`` Protocol -- the security-critical
half of the spine.

Everything here persists through the SAME tenant-scoped, version-checked ledger the run/worker
substrate uses (``api/services/production/state_substrate``). No new store engine, no new table:
accounts are ``kind="account"`` records, invites are ``kind="invite"``, and email uniqueness is an
auxiliary ``kind="account_email_index"`` record. The ledger's optimistic concurrency
(``VersionConflict``) is what makes the two hard guarantees real:

* **Single redemption under a race.** ``redeem_invite`` advances the invite's use-count with
  ``put(expected_version=<the version it read>)``. Two concurrent redeemers read the same version;
  the store lets exactly ONE ``put`` succeed and raises ``VersionConflict`` on the other. The loser
  fails closed (4xx). A single-use invite therefore cannot mint two accounts, even under
  simultaneous requests.
* **Email uniqueness.** A new account also writes an ``account_email_index`` record at
  ``expected_version=0``. If the email is already taken, that create raises ``VersionConflict`` --
  two accounts can never share one normalized email.

Storage tenant vs granted tenant (deliberate, and important):
The ledger requires a ``tenant_id`` on every read/write. Account-domain records (invite, account,
email index) are stored under ONE fixed *storage* tenant (``self._tenant``), so an invite is
resolvable by its code alone -- the redeemer presents only a code, never a tenant. The tenant a
redeemed account is *granted* (the ``tenant_id`` it carries into its token claims) is a server-side
fact taken from the invite, stored in the account PAYLOAD, and surfaced as a claim. Per-customer
tenant *partitioning* of these records (a real ``tenant_id`` as the storage key) is a later PR;
until then the records are durable and live under one accounts tenant. This is honest: the records
are durable and tenant-scoped at the storage layer; the granted-tenant value is just not yet the
storage key.

App wiring: the durable store is opened once at app startup (``api/main.py`` lifespan) using the
same backend selection as the state ledger (``_build_state_store`` -- Postgres when
``NC_DATABASE_URL`` is set, else SQLite) and stashed on ``app.state.account_store``. When
``accounts_enabled`` is True but no durable backend can be built, startup FAILS LOUD -- account
state never silently falls back to memory.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Optional

from api.services.crm.models import normalize_email
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

from .invites import generate_invite_code, is_redeemable
from .models import (
    ACCOUNT_EMAIL_INDEX_KIND,
    ACCOUNT_KIND,
    DEFAULT_INVITE_ROLE,
    INVITE_KIND,
    Account,
    InviteCode,
    Role,
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

    def __init__(self, store: StateStore, *, storage_tenant: str = ACCOUNTS_STORAGE_TENANT) -> None:
        self._store = store
        # The single ledger tenant every account-domain record is keyed under.
        self._tenant = storage_tenant

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
        invite = InviteCode(
            code=code or generate_invite_code(),
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

    # --- the security-critical redeem -------------------------------------

    def redeem_invite(
        self,
        *,
        code: str,
        email_or_username: str,
        display_name: Optional[str] = None,
    ) -> Account:
        """Redeem an invite into EXACTLY ONE account, atomically and fail-closed.

        Fail-closed contract -- any of these rejects with :class:`InviteRedemptionError` and
        creates NOTHING:

        * the code does not exist (``unknown_code``),
        * the code is expired or has no uses left (``not_redeemable``),
        * the invite pins a ``target_email`` and the supplied identity does not match it
          (``email_mismatch``),
        * the supplied identity is blank (``invalid_identity``),
        * the email already belongs to a different account (``email_taken``),
        * a concurrent redeem won the use-count race (``race_lost``).

        Atomicity -- two mechanisms, both backed by the ledger's optimistic concurrency:

        1. The account's ``account_id`` is DERIVED DETERMINISTICALLY from ``(code, normalized
           email)``, and the account is created before the invite use-count is advanced. So two
           concurrent redeems of the same code for the same identity converge on the *same* account
           -- a re-delivery returns the existing account, never a second one.
        2. The use-count is advanced with ``put(expected_version=<version read>)``. Under a race
           the store admits exactly one such ``put`` and raises ``VersionConflict`` on the rest, so
           a single-use invite cannot be spent twice. The loser fails closed.

        SERVER-DERIVED claims: the returned account's ``role``/``tenant_id`` come from the INVITE
        record, and ``account_id`` is server-computed. None of these are read from caller input --
        a client cannot smuggle a role or tenant through this call.
        """
        normalized_email = normalize_email(email_or_username)
        if not normalized_email:
            raise InviteRedemptionError("invalid_identity")

        # 1. Resolve the invite. ``None`` -> unknown code (fail closed, no mutation).
        invite_record = self._read_invite_record(code)
        if invite_record is None:
            raise InviteRedemptionError("unknown_code")
        invite = InviteCode.from_payload(invite_record.payload)
        version_seen = invite_record.version

        # 2. Idempotent re-delivery check FIRST. The account id is deterministic in (code,email), so
        #    if this exact redemption already produced an account, return it -- even for a now-
        #    exhausted single-use invite, because the use it would consume was ALREADY consumed by
        #    that prior redemption. Checking this before the redeemability gate is what makes a
        #    re-delivery converge on ONE account rather than tripping ``not_redeemable``.
        account_id = _account_id_for(code=code, normalized_email=normalized_email)
        existing = self.get_account_by_id(account_id)
        if existing is not None:
            return existing

        # 3. Usability checks (pure; no mutation on failure). Reached only for a genuinely NEW
        #    (code,email) redemption.
        if not is_redeemable(invite):
            raise InviteRedemptionError("not_redeemable")
        if invite.target_email is not None and invite.target_email != normalized_email:
            # A pinned invite may be redeemed only by its target identity.
            raise InviteRedemptionError("email_mismatch")

        # 4. Create the account + email-uniqueness index. The index create at expected_version=0
        #    is the email-uniqueness gate: a DIFFERENT account already holding this email makes the
        #    index put raise VersionConflict -> email_taken (no invite consumed). A conflict that
        #    resolves to THIS account_id is an idempotent re-entry, not a collision.
        now = datetime.now(UTC).isoformat()
        account = Account(
            account_id=account_id,
            email_or_username=normalized_email,
            role=normalize_role(invite.role),  # SERVER-DERIVED from the invite, not the request
            tenant_id=invite.tenant_id,        # SERVER-DERIVED granted tenant, not the request
            status="active",
            display_name=_clean_display_name(display_name),
            created_at=now,
            updated_at=now,
        )
        self._claim_email(normalized_email, account_id=account_id)
        account_record = LedgerRecord.new(
            tenant_id=self._tenant,
            kind=ACCOUNT_KIND,
            record_id=account_id,
            payload=account.to_payload(),
            parent_ids=(invite_record.record_id,),
            source="accounts.redeem_invite",
            trace_id=account_id,
        )
        try:
            self._store.put(account_record, expected_version=0)
        except VersionConflict:
            # A concurrent redeem of the SAME (code,email) created this exact account between our
            # existence check and our create. Idempotent: return the now-present account rather
            # than minting a second or surfacing a raw conflict.
            already = self.get_account_by_id(account_id)
            if already is not None:
                return already
            raise

        # 5. Commit the redemption by advancing the invite use-count. This is the race gate: the
        #    put is version-checked against the version we read in step 1, so a concurrent redeem
        #    that already advanced the invite makes THIS put raise VersionConflict.
        redeemed_invite = InviteCode(
            code=invite.code,
            role=invite.role,
            tenant_id=invite.tenant_id,
            target_email=invite.target_email,
            expires_at=invite.expires_at,
            max_uses=invite.max_uses,
            uses=invite.uses + 1,
            redeemed_by=invite.redeemed_by or account_id,
            redeemed_at=invite.redeemed_at or now,
            created_at=invite.created_at,
        )
        updated_record = invite_record.with_payload(redeemed_invite.to_payload())
        try:
            self._store.put(updated_record, expected_version=version_seen)
        except VersionConflict as exc:
            # A concurrent redeem advanced the invite between our read and our write. We already
            # created an account above, but it is deterministically keyed to THIS (code,email). To
            # keep a single-use invite single-use, the loser must fail closed; best-effort roll back
            # the account + email index we wrote so a rejected redeem leaves no orphan account.
            # Rollback failures never mask the race signal.
            self._rollback_account(account_id, normalized_email)
            raise InviteRedemptionError("race_lost") from exc

        return account

    # --- helpers -----------------------------------------------------------

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

    def _rollback_account(self, account_id: str, normalized_email: str) -> None:
        """Best-effort removal of an account + email index written by a redeem that then lost the
        use-count race. Never raises -- a rollback failure must not mask the original race signal.
        """
        for kind, record_id in (
            (ACCOUNT_KIND, account_id),
            (ACCOUNT_EMAIL_INDEX_KIND, _email_index_id(normalized_email)),
        ):
            try:
                current = self._store.get(self._tenant, kind, record_id)
                if current is not None:
                    self._store.delete(
                        self._tenant, kind, record_id, expected_version=current.version
                    )
            except Exception:
                # Swallow: rollback is best-effort cleanup, not a correctness dependency.
                pass


def _clean_display_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = raw.strip()
    return text or None


def _invite_record_id(code: str) -> str:
    """Deterministic record-id for an invite, derived from a digest of its code.

    The code itself is the secret; the record-id is a non-secret digest so the code is not stored
    in the id slot in the clear while remaining a stable lookup key.
    """
    digest = hashlib.sha256(f"invite:{code}".encode("utf-8")).hexdigest()[:32]
    return f"{_INVITE_ID_PREFIX}-{digest}"


def _email_index_id(normalized_email: str) -> str:
    digest = hashlib.sha256(f"email:{normalized_email}".encode("utf-8")).hexdigest()[:32]
    return f"acctemail-{digest}"


def _account_id_for(*, code: str, normalized_email: str) -> str:
    """Server-derived, deterministic account id bound to (invite code, normalized email).

    Determinism is what makes redemption idempotent under a re-delivery: the same (code,email)
    always maps to the same account_id, so a duplicate redeem cannot mint a second account.
    """
    digest = hashlib.sha256(
        f"account:{code}:{normalized_email}".encode("utf-8")
    ).hexdigest()[:32]
    return f"{_ACCOUNT_ID_PREFIX}-{digest}"
