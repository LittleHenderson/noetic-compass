"""Sessions service -- the revocation half of the PAID-user security spine.

Real, durable sessions: a :class:`Session` (the record a login produces and a token's ``jti`` is
checked against), persisted through the durable ``StateStore`` Protocol. This is the companion to
the accounts service (``api/services/accounts``): accounts give a token an *identity*; sessions give
that token *revocability and chokepoint expiry*. Wired into the live app behind the SAME
``accounts_enabled`` flag (default off) that gates accounts -- a login that resolves to an account
also opens a session, and the dispatch middleware enforces it.

Public surface kept small on purpose: the model, the store, and the ``build_session_store`` lifespan
helper that selects the same durable backend as the state ledger and FAILS LOUD when accounts are
enabled but no durable backend can be obtained.
"""

from __future__ import annotations

from .models import SESSION_KIND, Session
from .store import SessionStore


def build_session_store(settings) -> SessionStore | None:
    """Open the durable session store for app startup, or return ``None`` when accounts are off.

    Mirrors :func:`api.services.accounts.build_account_store` exactly -- sessions share the
    accounts_enabled flag because a session is only meaningful once identity login is on.

    Dark path: ``settings.accounts_enabled`` False (the default) -> return ``None``. The app behaves
    exactly as today; ``/auth/token`` keeps the shared-secret mint, no ``jti`` is embedded, and the
    dispatch middleware does no session lookup (legacy no-jti tokens flow untouched).

    Enabled path: select the SAME durable backend the state ledger uses
    (:func:`api.state_ledger_bootstrap._build_state_store` -- a ``PostgresStateStore`` when
    ``NC_DATABASE_URL`` is set, else a single-host ``SqliteStateStore``) and wrap it in a
    :class:`SessionStore`. Session records partition the store by their own ``kind="session"``, so
    they coexist with account and ledger records under one backend.

    Fail-loud: if accounts are enabled but the durable store cannot be built (unwritable SQLite path,
    unreachable/misconfigured Postgres), the underlying constructor raises and that error propagates
    -- startup fails visibly rather than silently degrading session state to memory. Session state is
    durable or absent, never ephemeral-but-pretending. (A session store that forgot on restart would
    silently log every user out on every redeploy AND, worse, make a "revoked" session forgettable.)
    """
    if not getattr(settings, "accounts_enabled", False):
        return None

    # Import lazily so the dark default never imports the backend selection (and its drivers).
    from api.state_ledger_bootstrap import _build_state_store

    store = _build_state_store(settings)
    return SessionStore(store)


__all__ = [
    "Session",
    "SESSION_KIND",
    "SessionStore",
    "build_session_store",
]
