"""Accounts service -- the identity half of the PAID-user security spine.

Real, durable identity: an :class:`Account` (the entity a JWT is minted against) and an
:class:`InviteCode` (a cryptographically-random, fail-closed redemption credential), both
persisted through the durable ``StateStore`` Protocol. This is NOT the import-isolated billing
stub (``api/services/production/billing.py``); it is wired into the live app behind the
``accounts_enabled`` flag (default off).

Public surface kept small on purpose: the models, the store + its redemption error, and the
``build_account_store`` lifespan helper that selects the same durable backend as the state ledger
and FAILS LOUD when accounts are enabled but no durable backend can be obtained.
"""

from __future__ import annotations

from api.services.production.state_substrate import StateStore

from .invites import generate_invite_code, is_redeemable
from .models import (
    Account,
    AccountStatus,
    DEFAULT_INVITE_ROLE,
    InviteCode,
    Role,
    ROLE_VALUES,
)
from .store import AccountStore, InviteRedemptionError


def build_account_store(settings) -> AccountStore | None:
    """Open the durable account store for app startup, or return ``None`` when accounts are off.

    Dark path: ``settings.accounts_enabled`` False (the default) -> return ``None``. The app
    behaves exactly as today; ``/auth/token`` keeps the shared-secret mint, and the account routes
    return 503 (accounts unavailable).

    Enabled path: select the SAME durable backend the state ledger uses
    (:func:`api.state_ledger_bootstrap._build_state_store` -- a ``PostgresStateStore`` when
    ``NC_DATABASE_URL`` is set, else a single-host ``SqliteStateStore``) and wrap it in an
    :class:`AccountStore`. Account/invite records partition the store by their own ``kind``s, so
    they coexist with any ledger records under one backend.

    Fail-loud: if accounts are enabled but the durable store cannot be built (unwritable SQLite
    path, unreachable/misconfigured Postgres), the underlying constructor raises and that error
    propagates -- startup fails visibly rather than silently degrading account state to memory.
    Account state is durable or absent, never ephemeral-but-pretending.
    """
    if not getattr(settings, "accounts_enabled", False):
        return None

    # Import lazily so the dark default never imports the backend selection (and its drivers).
    from api.state_ledger_bootstrap import _build_state_store

    store: StateStore = _build_state_store(settings)
    return AccountStore(
        store, credential_pepper=settings.account_credential_pepper
    )


__all__ = [
    "Account",
    "AccountStatus",
    "Role",
    "ROLE_VALUES",
    "DEFAULT_INVITE_ROLE",
    "InviteCode",
    "AccountStore",
    "InviteRedemptionError",
    "build_account_store",
    "generate_invite_code",
    "is_redeemable",
]
