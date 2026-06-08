"""Central authorization dependency -- the ONE place a privileged route is gated by role.

The dispatch middleware (``api/middleware/auth.py``) is the only thing that writes identity onto a
request: after it verifies a token's signature + expiry (and, for an account-mode token, that the
session is live and the account is not disabled) it sets ``request.state.role`` /
``request.state.tenant_id`` / ``request.state.account_id`` from the SERVER-side session+account
records. This module is the only place those server-set values are read to make an allow/deny.

Two rules, deliberately uniform across every privileged route:

* **No authenticated identity -> 401.** There is no server-set role on the request (the caller
  reached a route that did not establish account-mode identity). This is "who are you?", not "you
  may not": 401.
* **Authenticated but role not permitted -> 403.** A real identity is present but its role is not in
  the allowed set. This is "I know who you are, and you may not": 403, never 500, never a leak of
  what the resource is.

Why read ONLY ``request.state`` and never the body: the role/tenant/account on ``request.state`` are
server-derived (account record -> session record -> token claim -> dispatch attach). A request body
is attacker-controlled; a role check that consulted it would be trivially escalatable. ``require_role``
therefore never looks at the body, the query string, or the raw token -- only at what the server set.

Honesty about the dark default: when ``accounts_enabled`` is off, no token carries a ``jti`` and the
dispatch path never sets ``request.state.role``. A route guarded by ``require_role`` would then see
no identity and return 401 -- which is correct: role-gated routes are an accounts-mode feature, and
in the legacy shared-secret posture there are no roles to honour. (The endpoints wired to
``require_role`` in this PR -- invite creation -- are accounts-mode operator actions by construction.)
"""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import HTTPException, Request

from api.config import settings


def _server_role(request: Request) -> Optional[str]:
    """Return the SERVER-SET role for this request, or ``None`` when no identity was established.

    Reads only ``request.state.role`` -- the value the dispatch middleware attached from the
    account+session records. Never consults the body/query/token. A missing attribute (no
    account-mode identity on this request) is ``None``, which the callers map to 401.
    """
    role = getattr(request.state, "role", None)
    if role is None:
        return None
    text = str(role).strip()
    return text or None


def require_role(*roles: str) -> Callable[[Request], str]:
    """Build a FastAPI dependency that admits a request only if its server-set role is permitted.

    Usage::

        @router.post("/thing", dependencies=[Depends(require_role("operator", "admin", "owner"))])
        async def create_thing(...): ...

    Semantics:

    * no server-set identity on the request -> **401** ("Authentication required.");
    * identity present but ``request.state.role`` not in ``roles`` -> **403**
      ("This action requires one of: ...");
    * otherwise -> returns the caller's role (so a handler may use it without re-reading state).

    The allowed ``roles`` are a fixed, server-side allowlist baked into the route definition -- not
    read from the request -- so a caller cannot widen the set. Passing no roles is a programming
    error (a guard that admits everyone is never what a privileged route wants) and is refused at
    dependency-build time, loudly, rather than silently allowing all.
    """
    allowed = tuple(dict.fromkeys(r for r in roles if r))  # de-dupe, preserve order, drop blanks
    if not allowed:
        raise ValueError("require_role(...) needs at least one non-empty role")

    def _dependency(request: Request) -> str:
        role = _server_role(request)
        if role is None:
            # No authenticated identity established for this request.
            raise HTTPException(status_code=401, detail="Authentication required.")
        if role not in allowed:
            # Authenticated, but not permitted. 403 (not 500, not a resource leak).
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of: {', '.join(allowed)}.",
            )
        return role

    return _dependency


def current_account(request: Request) -> str:
    """Return the SERVER-SET ``account_id`` for the request, or raise 401 when there is none.

    A helper for handlers/dependencies that need the authenticated account id. Reads only
    ``request.state.account_id`` (server-derived); never the body. Absent identity -> 401.
    """
    account_id = getattr(request.state, "account_id", None)
    text = str(account_id).strip() if account_id is not None else ""
    if not text:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return text


def current_tenant(request: Request) -> str:
    """Return the SERVER-SET ``tenant_id`` for the request, or raise 401 when there is none.

    A helper for tenant-scoped handlers. Reads only ``request.state.tenant_id`` (server-derived from
    the account/session, carried as a token claim, attached at dispatch); never the body. Absent
    identity -> 401. This is the seam per-tenant data scoping (Phase 3) will consume; here it simply
    surfaces the server-derived tenant for any route that asks.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    text = str(tenant_id).strip() if tenant_id is not None else ""
    if not text:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return text


def require_role_in_account_mode(*roles: str) -> Callable[[Request], Optional[str]]:
    """Build a role gate that is LIVE only when accounts are enabled, and a no-op otherwise.

    This is the conditional sibling of :func:`require_role`. It exists for routes that are
    unconditionally reachable today under the legacy shared-secret posture and must STAY reachable
    there byte-for-byte, but that become operator-only once per-account identity is turned on.

    Semantics:

    * ``settings.accounts_enabled`` is False (the dark default) -> the dependency returns ``None``
      and performs NO role check. In that posture the dispatch path never sets ``request.state.role``
      (there are no roles to honour), so an unconditional :func:`require_role` here would 401 every
      legacy caller. Returning ``None`` preserves the exact legacy behaviour: the route is gated only
      by the legacy Bearer token the middleware already validated.
    * ``settings.accounts_enabled`` is True -> the dependency behaves EXACTLY like
      ``require_role(*roles)``: no server-set identity -> **401**; identity present but role not in
      ``roles`` -> **403**; otherwise the caller's role is returned.

    ``settings.accounts_enabled`` is read at REQUEST time (per call), not captured at
    dependency-build time, so flipping the flag (as the test fixtures do) takes effect immediately.
    The allowed ``roles`` are a fixed server-side allowlist baked into the route definition; passing
    none is the same programming error :func:`require_role` refuses, and is refused here too at
    build time rather than silently admitting everyone once accounts come on.
    """
    # Build the underlying live gate eagerly so the "no roles" programming error is caught at
    # import/route-definition time (loudly), exactly as ``require_role`` does -- not deferred to the
    # first account-mode request.
    live_gate = require_role(*roles)

    def _dependency(request: Request) -> Optional[str]:
        if not settings.accounts_enabled:
            # Dark default: complete no-op. No role check, no new failure mode -- legacy posture.
            return None
        # Account-mode: identical to require_role (401 no identity / 403 not permitted / role).
        return live_gate(request)

    return _dependency
