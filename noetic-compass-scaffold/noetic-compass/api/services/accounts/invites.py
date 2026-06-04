"""Server-side invite-code generation + the pure expiry / use-limit predicates.

Two responsibilities, both deliberately small and side-effect-free so the security-critical
redeem path in ``store.py`` can reason about an invite with no I/O:

1. :func:`generate_invite_code` mints a cryptographically random code via
   ``secrets.token_urlsafe``. This is the ONLY place a code is created; a code is never derived
   from caller input, an email, or a timestamp -- anything guessable would let an attacker forge
   an invite. ``secrets`` (not ``random``) is mandatory: it is the stdlib CSPRNG.

2. :func:`is_expired` / :func:`uses_remaining` / :func:`is_redeemable` are the pure checks the
   redeem path consults BEFORE it mutates anything. Keeping them here (not inline in the store)
   makes the fail-closed policy a single, directly-testable unit: an invite is redeemable iff it
   has not expired AND has uses remaining.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Optional

from .models import InviteCode

# Default entropy for a code. ``token_urlsafe(n)`` returns ~1.3*n URL-safe characters from n random
# bytes; 32 bytes = 256 bits of entropy, far beyond brute-force reach. URL-safe so a code can ride
# in a link or a JSON body without escaping.
_DEFAULT_CODE_BYTES = 32


def generate_invite_code(*, num_bytes: int = _DEFAULT_CODE_BYTES) -> str:
    """Return a fresh, cryptographically random, URL-safe invite code.

    Uses ``secrets.token_urlsafe`` (the stdlib CSPRNG) -- never ``random``. The result is
    unguessable, which is what lets an invite code stand in as a bearer credential for redemption.
    """
    if num_bytes < 16:
        # Refuse to mint a weak code. 16 bytes = 128 bits is the floor for a bearer credential.
        raise ValueError("invite code must be at least 16 bytes of entropy")
    return secrets.token_urlsafe(num_bytes)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp to an aware UTC datetime, tolerating a missing value.

    A value that is present but unparseable is treated as *already expired* (returns the epoch)
    rather than ignored -- a corrupt expiry must fail closed, never silently mean "no expiry".
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


def is_expired(invite: InviteCode, *, now: Optional[datetime] = None) -> bool:
    """True once ``invite.expires_at`` has passed. An invite with no expiry never expires.

    Expiry is ``>=`` (an invite expiring exactly now is expired), matching the lease-expiry
    convention in the state substrate so there is no instant an about-to-lapse invite is honoured.
    """
    expires = _parse_iso(invite.expires_at)
    if expires is None:
        return False
    return (now or datetime.now(UTC)) >= expires


def uses_remaining(invite: InviteCode) -> int:
    """How many redemptions are still available (never negative)."""
    return max(0, invite.max_uses - invite.uses)


def is_redeemable(invite: InviteCode, *, now: Optional[datetime] = None) -> bool:
    """The single fail-closed predicate: redeemable iff not expired AND uses remain.

    The redeem path checks this before mutating; if it is False the redeem is rejected with a 4xx
    and NOTHING is created. (Code *validity* -- "does this code exist at all" -- is the store's
    lookup; this predicate answers "is an existing code still usable".)
    """
    return uses_remaining(invite) > 0 and not is_expired(invite, now=now)
