"""Durable Session storage over the ``StateStore`` Protocol -- the revocation half of the spine.

Mirrors ``api/services/accounts/store.py`` exactly: sessions persist through the SAME tenant-scoped,
version-checked ledger the accounts and run/worker substrate use. No new store engine, no new table:
a session is a ``kind="session"`` record whose ``record_id`` IS the session id (and the token
``jti``), so a presented token resolves to its session with a single keyed read.

What the ledger's optimistic concurrency buys here:

* **Idempotent, single-writer revoke.** ``revoke_session`` reads the record, stamps ``revoked_at``,
  and writes back with ``put(expected_version=<version read>)``. A session already revoked is left
  as-is (the first revoke's timestamp stands); a concurrent revoke that already advanced the record
  makes the loser's version-checked write raise :class:`VersionConflict`, and we treat that as
  "already revoked by someone else" -- the post-condition (session is dead) holds either way.

Storage tenant vs granted tenant (same deliberate split as accounts):
The ledger requires a ``tenant_id`` on every read/write. Session records are stored under ONE fixed
*storage* tenant (``self._tenant``) so a token resolves to its session by ``jti`` alone -- the
dispatch path presents only the ``jti`` from the token, never a tenant. The tenant the session
*grants* (carried into ``request.state.tenant_id``) is a server-side fact taken from the account at
login and stored in the session PAYLOAD. Per-customer tenant *partitioning* of session records (a
real ``tenant_id`` as the storage key) is later work; until then the records are durable and live
under one sessions tenant. This is honest: durable and tenant-scoped at the storage layer; the
granted-tenant value is just not yet the storage key.

App wiring: opened once at app startup (``api/main.py`` lifespan) using the same backend selection
as the state ledger (``_build_state_store`` -- Postgres when ``NC_DATABASE_URL`` is set, else
SQLite) and stashed on ``app.state.session_store``. When ``accounts_enabled`` is True but no durable
backend can be built, startup FAILS LOUD -- session state never silently falls back to memory.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)

from .models import SESSION_KIND, Session, _utc_now_iso

# The single storage tenant all session records live under (see module docstring). This is the
# ledger storage key, NOT the tenant a session grants -- that granted tenant is a payload fact
# carried into ``request.state``. Per-customer storage partitioning is later work.
SESSIONS_STORAGE_TENANT = "sessions"


class SessionStore:
    """Durable session store over a single :class:`StateStore` backend.

    Methods mirror the accounts store's shape: a ``create_*`` that mints + persists, a ``get_*`` that
    reads by id (fail-closed to ``None``), a state-changing ``revoke_*``, and a best-effort
    ``touch_*``. The session id is server-minted here and used verbatim as the token ``jti``.
    """

    def __init__(self, store: StateStore, *, storage_tenant: str = SESSIONS_STORAGE_TENANT) -> None:
        self._store = store
        # The single ledger tenant every session record is keyed under.
        self._tenant = storage_tenant

    # --- create ------------------------------------------------------------

    def create_session(
        self,
        *,
        account_id: str,
        tenant_id: str,
        role: str,
        expires_at: Optional[str] = None,
        session_id: Optional[str] = None,
        source: str = "sessions.create_session",
    ) -> Session:
        """Mint and persist a new session for an authenticated login.

        ``account_id``/``tenant_id``/``role`` are SERVER-DERIVED facts copied from the account record
        by the login path -- never from a request body. ``session_id`` is server-minted (a fresh
        random id) unless one is supplied (tests may pin one); it becomes both the ledger record id
        and the token ``jti``. ``expires_at`` should mirror the token's own expiry so a session never
        outlives the credential it backs.

        The create uses ``put(expected_version=0)``: a fresh, unique id cannot collide, so this
        always creates rather than races. The record's ``parent_ids`` points at the account, giving
        the session the project's load-bearing object traceability for free.
        """
        sid = session_id or _new_session_id()
        now = _utc_now_iso()
        session = Session(
            session_id=sid,
            account_id=account_id,
            tenant_id=tenant_id,
            role=role,
            issued_at=now,
            expires_at=expires_at,
            revoked_at=None,
            last_seen=now,
        )
        record = LedgerRecord.new(
            tenant_id=self._tenant,
            kind=SESSION_KIND,
            record_id=sid,
            payload=session.to_payload(),
            parent_ids=(account_id,),
            source=source,
            trace_id=sid,
        )
        # expected_version=0 -> create. A server-minted random id makes a collision astronomically
        # unlikely; a pinned duplicate (tests) would raise VersionConflict, which we surface.
        self._store.put(record, expected_version=0)
        return session

    # --- read --------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[Session]:
        """Look up a session by its id (== token ``jti``). Returns ``None`` for an absent id.

        This is the lookup the dispatch middleware uses: given the ``jti`` from a verified token,
        find the durable session whose live/revoked/expired state gates the request. Fail closed --
        an unknown ``jti`` (e.g. a session that never existed, or was hard-deleted) returns ``None``
        and the chokepoint treats that as 401.
        """
        record = self._read_session_record(session_id)
        if record is None:
            return None
        return Session.from_payload(record.payload)

    # --- revoke (logout / admin) ------------------------------------------

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session by id. Returns True if a session was found (and is now revoked).

        Idempotent and fail-closed:

        * Unknown id -> returns False (nothing to revoke; the caller's logout is a no-op success).
        * Already revoked -> returns True without rewriting (the first revoke's timestamp stands).
        * Live session -> stamps ``revoked_at`` and writes back version-checked. A concurrent revoke
          that already advanced the record makes this version-checked write raise
          :class:`VersionConflict`; we re-read and, if the record is now revoked, treat it as done
          (the post-condition -- session is dead -- holds regardless of who won).

        After a successful revoke, the NEXT request bearing this session's token is rejected at the
        dispatch chokepoint (the middleware looks the session up and sees ``revoked_at`` set).
        """
        record = self._read_session_record(session_id)
        if record is None:
            return False
        session = Session.from_payload(record.payload)
        if session.is_revoked:
            return True
        revoked = Session(
            session_id=session.session_id,
            account_id=session.account_id,
            tenant_id=session.tenant_id,
            role=session.role,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            revoked_at=datetime.now(UTC).isoformat(),
            last_seen=session.last_seen,
        )
        try:
            self._store.put(record.with_payload(revoked.to_payload()), expected_version=record.version)
        except VersionConflict:
            # A concurrent writer advanced the record between our read and our write. Re-read: if it
            # is now revoked, the goal is met; otherwise surface the conflict honestly.
            current = self.get_session(session_id)
            if current is not None and current.is_revoked:
                return True
            raise
        return True

    # --- touch (best-effort last-seen) ------------------------------------

    def touch_session(self, session_id: str, *, when: Optional[str] = None) -> None:
        """Advance ``last_seen`` for a live session. Best-effort -- never raises, never blocks auth.

        Pure observability (when did this session last make a request): a failure here -- absent
        session, a concurrent write winning the version race -- is swallowed, because last-seen is
        not a correctness dependency and must never turn a valid request into an error. A revoked or
        expired session is left untouched (there is nothing useful to record, and we must not
        resurrect a dead session's timestamp).
        """
        try:
            record = self._read_session_record(session_id)
            if record is None:
                return
            session = Session.from_payload(record.payload)
            if not session.is_live():
                return
            touched = Session(
                session_id=session.session_id,
                account_id=session.account_id,
                tenant_id=session.tenant_id,
                role=session.role,
                issued_at=session.issued_at,
                expires_at=session.expires_at,
                revoked_at=session.revoked_at,
                last_seen=when or _utc_now_iso(),
            )
            self._store.put(
                record.with_payload(touched.to_payload()), expected_version=record.version
            )
        except Exception:
            # Swallow: last-seen is best-effort cleanup, not a correctness dependency.
            pass

    # --- helpers -----------------------------------------------------------

    def _read_session_record(self, session_id: str) -> Optional[LedgerRecord]:
        """Read the raw session ledger record (so callers also get its version).

        Sessions live under the single storage tenant, so a ``jti`` resolves without a tenant hint --
        which is essential: the dispatch path presents only the ``jti`` from the token.
        """
        sid = (session_id or "").strip()
        if not sid:
            return None
        return self._store.get(self._tenant, SESSION_KIND, sid)


def _new_session_id() -> str:
    """Server-minted, opaque, unique session id -- used verbatim as the token ``jti``.

    Reuses the substrate's ``new_record_id`` style (``<prefix>-<uuid4hex>``) so session ids are
    human-greppable and collision-free. A session id is an opaque handle, not a secret: it only
    *names* a session whose live/revoked state the store is the authority on. (A stolen token is
    dangerous because of its SIGNATURE, not because the ``jti`` is guessable -- revocation is exactly
    the defence against a stolen-but-still-signed token.)
    """
    from api.services.production.state_substrate import new_record_id

    return new_record_id("sess")
