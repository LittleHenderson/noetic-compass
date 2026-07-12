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
from api.services.production.state_substrate import StateStore

from .store import SessionStore


def build_session_store(
    settings, *, store: StateStore | None
) -> SessionStore | None:
    """Wrap the same lifespan-owned persistent store used by accounts."""
    if not getattr(settings, "accounts_enabled", False):
        return None
    if store is None:
        raise RuntimeError("Account mode requires a shared persistent StateStore.")

    from api.services.production.state_substrate import InMemoryStateStore

    if isinstance(store, InMemoryStateStore):
        raise RuntimeError("Account mode refuses the transient in-memory StateStore.")
    return SessionStore(store)


__all__ = [
    "Session",
    "SESSION_KIND",
    "SessionStore",
    "build_session_store",
]
