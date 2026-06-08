"""Session value object -- the second half of the PAID-user security spine.

A :class:`Session` is the durable record a login produces and a request's token is checked
against. PR #1 gave the app a real :class:`~api.services.accounts.models.Account` (the identity a
token is minted *for*); this record is what makes a minted token *revocable* and *expirable at the
chokepoint* rather than only at issue time. The token embeds the session's ``session_id`` as its
``jti`` claim; the dispatch middleware looks the session up by that ``jti`` on every request and
fails closed (401) when the session is missing, revoked, or expired -- which is what turns "logout"
and "disable account" into something enforced on the NEXT request, not merely at the next login.

Persistence note: sessions are stored through the SAME durable ``StateStore`` Protocol the accounts
and run/worker substrate use, as record ``kind="session"`` (see ``store.py``). The ledger envelope
(``parent_ids``/``source``/``trace_id``) carries object traceability for free -- a session record
knows the account it descends from. ``session_id`` IS the ledger ``record_id`` AND the token
``jti``, so a token resolves to its session with no secondary index.

Honesty: a session is a record of an authenticated login, nothing more. It does not imply a paid
plan, a quota grant, or any proof verdict -- those are separate concerns (Phase 4). Holding a live
session means the token has not been revoked and has not expired; it does not mean "entitled."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Optional


# Schema version stamped into the persisted payload so a future migration can tell which shape a
# stored record was written under. Mirrors ``ACCOUNT_SCHEMA_VERSION`` in accounts/models.py.
SESSION_SCHEMA_VERSION = "cas_sessions.session.v1"

# Ledger record kind. The generic ``kind``-keyed ``ledger_records`` table holds these; no new store
# engine or table is introduced (the StateStore is the single persistence seam).
SESSION_KIND = "session"


def _utc_now_iso() -> str:
    """ISO-8601, timezone-aware UTC -- matches the account/audit-session timestamp format."""
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Session:
    """A durable record of one authenticated login -- the thing a token's ``jti`` resolves to.

    ``session_id`` is SERVER-MINTED, opaque, and unique; it is both the ledger ``record_id`` and the
    token's ``jti`` claim. ``account_id``/``tenant_id``/``role`` are copied from the account record
    at login time so the dispatch path can attach a server-derived identity without a second account
    read on the hot path (the account *status* is still re-checked at dispatch, so a disable still
    takes effect immediately -- see the middleware). ``revoked_at`` is set by logout/admin-revoke;
    once set, the session is dead. ``expires_at`` matches the token's own expiry so a session never
    outlives the credential it backs.
    """

    session_id: str
    account_id: str
    tenant_id: str
    role: str
    issued_at: str = field(default_factory=_utc_now_iso)
    expires_at: Optional[str] = None  # ISO-8601 UTC; None == no independent session expiry
    revoked_at: Optional[str] = None  # ISO-8601 UTC; set once, by logout/admin-revoke
    last_seen: Optional[str] = None  # ISO-8601 UTC; advanced by touch_session (best-effort)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, *, now: Optional[datetime] = None) -> bool:
        """True once ``expires_at`` has passed. A session with no expiry never expires here.

        Expiry is ``>=`` (a session expiring exactly now is expired), matching the lease/invite
        expiry convention in the substrate so there is no instant an about-to-lapse session is
        honoured. The token also carries its own ``exp``; this is the session-side backstop.
        """
        if self.expires_at is None:
            return False
        parsed = _parse_iso(self.expires_at)
        if parsed is None:
            return False
        return (now or datetime.now(UTC)) >= parsed

    def is_live(self, *, now: Optional[datetime] = None) -> bool:
        """The single fail-closed predicate the chokepoint consults: not revoked AND not expired."""
        return not self.is_revoked and not self.is_expired(now=now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "account_id": self.account_id,
            "tenant_id": self.tenant_id,
            "role": self.role,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "last_seen": self.last_seen,
        }

    def to_payload(self) -> dict[str, Any]:
        """The mapping persisted in a ``kind="session"`` ledger record's ``payload``."""
        payload = self.to_dict()
        payload["schema_version"] = SESSION_SCHEMA_VERSION
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Session":
        """Rebuild a :class:`Session` from a stored ledger payload."""
        return cls(
            session_id=str(payload["session_id"]),
            account_id=str(payload["account_id"]),
            tenant_id=str(payload["tenant_id"]),
            role=str(payload["role"]),
            issued_at=str(payload.get("issued_at") or _utc_now_iso()),
            expires_at=_opt_str(payload.get("expires_at")),
            revoked_at=_opt_str(payload.get("revoked_at")),
            last_seen=_opt_str(payload.get("last_seen")),
        )


def _opt_str(value: Any) -> Optional[str]:
    """Coerce to a non-empty string or ``None`` (treat blank/missing as absent)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp to an aware UTC datetime, tolerating a missing value.

    A value that is present but unparseable is treated as *already expired* (returns the epoch)
    rather than ignored -- a corrupt expiry must fail closed, never silently mean "no expiry".
    Mirrors the invite-expiry parser in ``accounts/invites.py``.
    """
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromtimestamp(0, tz=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
