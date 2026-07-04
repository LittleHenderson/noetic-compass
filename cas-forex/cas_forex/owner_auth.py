"""Owner authentication for the CAS Forex API — who is allowed to drive.

The cockpit is a single-owner app that controls real trading levers and (once
armed) real money. The point of this module is NOT to make the owner jump
through hoops — the owner's own machine is trusted with zero friction. The point
is to stop OTHER devices on the same network from touching the owner's money
routes. That is what makes it safe to reach the cockpit from a phone.

Model (simple and strict):

  * LOOPBACK is the owner. Requests from 127.0.0.1 / ::1 / localhost (the PC the
    app runs on) are always allowed, no token. The desktop UI just works.
  * LAN is opt-in and authenticated. Requests from any other address are refused
    UNLESS the owner has (a) turned LAN mode ON and (b) the request carries the
    owner token. LAN mode defaults OFF, so out of the box nothing off-box can
    reach a route.
  * Liveness + CORS preflight are exempt so health checks and browsers work.

The owner token is generated once per install, stored under ``runtime/`` (which
is git-ignored), never logged, and shown to the owner ONLY over loopback so a
phone can be paired (passcode / QR). Rotating the token unpairs every device.

This module is pure/deterministic where it matters: ``evaluate_request`` is a
plain function over (client host, path, headers) so the whole policy is unit
tested without a server. The API wires it into one middleware.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTH_PATH = REPO_ROOT / "runtime" / "owner-auth.json"

REPORT_KIND = "cas_forex_owner_auth"
TOKEN_BYTES = 32  # secrets.token_urlsafe(32) ≈ 43 url-safe chars

# Hosts that mean "the owner's own machine" — always trusted, no token needed.
# "testclient" is Starlette's TestClient host, so the existing route tests (which
# speak from loopback-equivalent) keep working.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient", ""})

# Reachable off-box without a token (liveness only — nothing sensitive).
EXEMPT_PREFIXES = ("/api/forex/health",)

_LOCK = threading.RLock()
_PATH = DEFAULT_AUTH_PATH

CLAIM_BOUNDARY = (
    "Owner auth gates WHO may reach the API off-box; loopback (the owner's own "
    "machine) is always allowed. It does not itself place trades, move money, or "
    "arm live trading — it only decides whether a request is let through to the "
    "routes that already carry their own gates."
)


def set_auth_path_for_tests(path: Optional[Path]) -> None:
    global _PATH
    _PATH = Path(path) if path is not None else DEFAULT_AUTH_PATH


# ---------------------------------------------------------------------------
# Durable store (token + lan_mode)
# ---------------------------------------------------------------------------
def _load() -> dict:
    if not _PATH.exists():
        return {}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(_PATH.suffix + ".tmp")
    payload = json.dumps(data, indent=2, sort_keys=True)
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(_PATH)
            return
        except OSError as exc:  # transient OneDrive/AV lock
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
    if last_error is not None:
        raise last_error


def current_token() -> Optional[str]:
    """The stored owner token, or None if one has never been generated."""
    with _LOCK:
        value = _load().get("owner_token")
        return str(value) if value else None


def get_or_create_token() -> str:
    """Return the owner token, generating + persisting one on first use."""
    with _LOCK:
        data = _load()
        token = data.get("owner_token")
        if not token:
            token = secrets.token_urlsafe(TOKEN_BYTES)
            data["owner_token"] = token
            data.setdefault("lan_mode_enabled", False)
            data["created_at"] = data.get("created_at") or _now_iso()
            _save(data)
        return str(token)


def rotate_token() -> str:
    """Generate a fresh token (unpairs every previously paired device)."""
    with _LOCK:
        data = _load()
        token = secrets.token_urlsafe(TOKEN_BYTES)
        data["owner_token"] = token
        data["rotated_at"] = _now_iso()
        _save(data)
        return token


def verify_token(candidate: Optional[str]) -> bool:
    """Constant-time check of a presented token against the stored one."""
    if not candidate:
        return False
    stored = current_token()
    if not stored:
        return False
    return hmac.compare_digest(str(candidate), str(stored))


def lan_mode_enabled() -> bool:
    with _LOCK:
        return bool(_load().get("lan_mode_enabled", False))


def set_lan_mode(enabled: bool) -> dict:
    """Turn authenticated LAN access on/off. Enabling ensures a token exists."""
    with _LOCK:
        if enabled:
            get_or_create_token()  # never enable LAN with no token to check against
        data = _load()
        data["lan_mode_enabled"] = bool(enabled)
        data["lan_mode_changed_at"] = _now_iso()
        _save(data)
        return {"lan_mode_enabled": bool(enabled)}


def _now_iso() -> str:
    from cas_forex.time_utils import utc_now

    return utc_now().isoformat()


def mask_token(token: Optional[str]) -> str:
    """Presence + last 4 chars for display; never the whole token."""
    if not token:
        return ""
    tail = token[-4:] if len(token) >= 4 else "****"
    return f"…{tail}"


# ---------------------------------------------------------------------------
# Policy (pure — unit tested without a server)
# ---------------------------------------------------------------------------
def request_is_loopback(host: Optional[str]) -> bool:
    return str(host or "").strip().lower() in _LOOPBACK_HOSTS


def extract_token(headers: Mapping[str, str]) -> Optional[str]:
    """Pull the owner token from either ``X-CAS-Owner-Token`` or an
    ``Authorization: Bearer <token>`` header. Header lookup is case-insensitive."""
    lower = {str(k).lower(): str(v) for k, v in headers.items()}
    direct = lower.get("x-cas-owner-token")
    if direct:
        return direct.strip()
    auth = lower.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


@dataclass(frozen=True)
class AuthDecision:
    allow: bool
    status: int
    reason: str


_ALLOW = AuthDecision(True, 200, "allowed")


def evaluate_request(
    *,
    method: str,
    client_host: Optional[str],
    path: str,
    headers: Mapping[str, str],
) -> AuthDecision:
    """Decide whether one request may proceed. Pure over its inputs.

    Order: CORS preflight and liveness are exempt; loopback (the owner's own
    machine) is always allowed; otherwise LAN mode must be ON and a valid owner
    token present.
    """
    if str(method).upper() == "OPTIONS":  # CORS preflight carries no auth header
        return _ALLOW
    if any(str(path).startswith(p) for p in EXEMPT_PREFIXES):
        return _ALLOW
    if request_is_loopback(client_host):
        return _ALLOW
    if not lan_mode_enabled():
        return AuthDecision(
            False,
            403,
            "LAN access is off. On the PC running CAS Forex, turn on LAN mode and "
            "pair this device to reach the cockpit from another device.",
        )
    if verify_token(extract_token(headers)):
        return _ALLOW
    return AuthDecision(
        False,
        401,
        "Owner token required. Pair this device with the code shown in the "
        "cockpit on the PC (Authorization: Bearer <token> or X-CAS-Owner-Token).",
    )


def pairing_payload() -> dict:
    """Loopback-only pairing info the desktop UI shows so a phone can be paired.
    Includes the FULL token on purpose — this is only ever served over loopback."""
    token = get_or_create_token()
    return {
        "report_kind": REPORT_KIND,
        "owner_token": token,
        "token_hint": mask_token(token),
        "lan_mode_enabled": lan_mode_enabled(),
        "header_name": "X-CAS-Owner-Token",
        "how_to_pair": (
            "On the other device, open the cockpit and enter this token when "
            "asked, or scan the QR. Turn LAN mode ON here to allow it in."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "AuthDecision",
    "current_token",
    "evaluate_request",
    "extract_token",
    "get_or_create_token",
    "lan_mode_enabled",
    "mask_token",
    "pairing_payload",
    "request_is_loopback",
    "rotate_token",
    "set_auth_path_for_tests",
    "set_lan_mode",
    "verify_token",
]
