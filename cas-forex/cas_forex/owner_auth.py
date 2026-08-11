"""Owner authentication for the CAS Forex API — who is allowed to drive.

The cockpit is a single-owner app that controls real trading levers and (once
armed) real money. The point of this module is NOT to make the owner jump
through hoops — the owner's own machine is trusted with zero friction. The point
is to stop OTHER devices on the same network from touching the owner's money
routes. That is what makes it safe to reach the cockpit from a phone.

Model (simple and strict):

  * LOOPBACK is the owner. Requests from 127.0.0.1 / ::1 / localhost (the PC the
    app runs on) are always allowed, no token. The desktop UI just works.
    If the local phone preview proxy forwards a non-loopback client address in
    X-Forwarded-For, CAS treats the caller as that phone rather than as
    loopback.
  * LAN is opt-in and authenticated. Requests from any other address are refused
    UNLESS the owner has (a) turned LAN mode ON and (b) the request carries the
    owner token. LAN mode defaults OFF, so out of the box nothing off-box can
    reach a route.
  * Liveness + CORS preflight are exempt so health checks and browsers work.
  * The built web shell is public for safe GET/HEAD requests. It contains no
    secrets and must load before a new phone/browser can paste the owner token.
    All protected state and controls stay under ``/api/*`` and remain gated.

The owner token is generated once per install, stored under ``runtime/`` as a
local encrypted envelope, never logged, and shown to the owner ONLY over
loopback so a phone can be paired (passcode / pairing link). Rotating the token
unpairs every device.

This module is pure/deterministic where it matters: ``evaluate_request`` is a
plain function over (client host, path, headers) so the whole policy is unit
tested without a server. The API wires it into one middleware.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import secrets
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.secret_envelope import (
    is_secret_envelope,
    protect_secret,
    secret_storage_status,
    unprotect_secret,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTH_PATH = REPO_ROOT / "runtime" / "owner-auth.json"
DEFAULT_PHONE_WEB_PORT = 4173
DEFAULT_PHONE_API_PORT = 8765
NATIVE_PAIRING_SCHEME = "casforex"

REPORT_KIND = "cas_forex_owner_auth"
PAIRING_HASH_KEY = "cas_owner_token"
API_BASE_HASH_KEY = "cas_api_base"
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
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    token_value = data.get("owner_token")
    if token_value is not None:
        try:
            token = unprotect_secret(token_value)
        except Exception:
            token = ""
        if token:
            data["owner_token"] = token
            if not is_secret_envelope(token_value):
                _save(data)
        else:
            data.pop("owner_token", None)
    return data


def _save(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(_PATH.suffix + ".tmp")
    payload_data = dict(data)
    token = str(payload_data.get("owner_token") or "").strip()
    if token:
        payload_data["owner_token"] = protect_secret(token)
    payload_data["secret_storage"] = secret_storage_status()
    payload_data["claim_boundary"] = (
        "Local owner-auth store. The owner token is stored as a local encrypted "
        "envelope; pairing responses may still show the full token only on "
        "loopback-only owner-auth routes."
    )
    payload = json.dumps(payload_data, indent=2, sort_keys=True)
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


def cloud_mode() -> bool:
    """True when the engine is hosted on the internet (a cloud server). A deploy
    sets ``CAS_FOREX_CLOUD_MODE=1``. In cloud mode loopback is NOT trusted — a
    reverse proxy in front of the app makes every request appear to come from
    127.0.0.1, so the owner token is required on everything."""
    return str(os.environ.get("CAS_FOREX_CLOUD_MODE", "")).strip().lower() in {"1", "true", "yes", "on"}


def current_token() -> Optional[str]:
    """The owner token. A deploy-time env override (``CAS_FOREX_OWNER_TOKEN``)
    wins — that's how a cloud host injects the owner's chosen token — otherwise
    the value stored in the encrypted local auth file."""
    env = os.environ.get("CAS_FOREX_OWNER_TOKEN")
    if env and env.strip():
        return env.strip()
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
def auth_store_status() -> dict[str, Any]:
    """Read-only owner-auth storage metadata. Does not expose the token."""
    storage = dict(secret_storage_status())
    return {
        "path": str(_PATH),
        "at_rest_encrypted": bool(storage.get("at_rest_encrypted")),
        "secret_storage": storage,
    }


def request_is_loopback(host: Optional[str]) -> bool:
    return _normalize_host(host) in _LOOPBACK_HOSTS


def effective_client_host(
    client_host: Optional[str],
    headers: Mapping[str, str],
) -> Optional[str]:
    """Return the caller host CAS should authorize against.

    The phone PWA normally reaches the backend through the local Vite preview
    proxy. That makes the TCP peer look like loopback while ``X-Forwarded-For``
    carries the actual phone address. Trust forwarded client headers only when
    the immediate peer is loopback; direct off-box callers cannot spoof their
    way into loopback by sending their own forwarding headers.
    """
    normalized_client = _normalize_host(client_host)
    forwarded = extract_forwarded_client_host(headers)
    if request_is_loopback(normalized_client) and forwarded:
        return forwarded
    return normalized_client


def extract_forwarded_client_host(headers: Mapping[str, str]) -> Optional[str]:
    lower = {str(k).lower(): str(v) for k, v in headers.items()}
    forwarded_for = lower.get("x-forwarded-for", "")
    if forwarded_for.strip():
        first = forwarded_for.split(",", 1)[0].strip()
        cleaned = _normalize_host(first)
        return cleaned or None
    real_ip = lower.get("x-real-ip", "")
    if real_ip.strip():
        cleaned = _normalize_host(real_ip)
        return cleaned or None
    return None


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


def _is_public_web_shell_request(method: str, path: str) -> bool:
    """Allow the static cockpit shell to load before owner-token pairing."""
    if str(method).upper() not in {"GET", "HEAD"}:
        return False
    return not str(path or "").startswith("/api/")


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
    machine) is always allowed; proxied phone requests use ``X-Forwarded-For``
    as the effective caller; otherwise LAN mode must be ON and a valid owner
    token present.
    """
    if str(method).upper() == "OPTIONS":  # CORS preflight carries no auth header
        return _ALLOW
    if any(str(path).startswith(p) for p in EXEMPT_PREFIXES):
        return _ALLOW
    if _is_public_web_shell_request(method, path):
        return _ALLOW
    # CLOUD MODE: on the internet (usually behind a reverse proxy that makes
    # every request look like loopback), NEVER trust loopback — require a valid
    # owner token on everything. HTTPS is assumed at the proxy (see DEPLOY.md).
    if cloud_mode():
        if verify_token(extract_token(headers)):
            return _ALLOW
        return AuthDecision(
            False,
            401,
            "Owner token required. Send Authorization: Bearer <token> or "
            "X-CAS-Owner-Token (set at deploy via CAS_FOREX_OWNER_TOKEN).",
        )
    caller_host = effective_client_host(client_host, headers)
    if request_is_loopback(caller_host):
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


def _normalize_host(host: Optional[str]) -> str:
    value = str(host or "").strip().strip('"').strip("'").lower()
    if not value:
        return ""
    if value.startswith("[") and "]" in value:
        return value[1 : value.index("]")]
    if value.startswith("::ffff:"):
        return value.removeprefix("::ffff:")
    if ":" in value and value.count(":") == 1:
        host_part, port_part = value.rsplit(":", 1)
        if port_part.isdigit():
            return host_part
    return value


def pairing_payload() -> dict:
    """Loopback-only pairing info the desktop UI shows so a phone can be paired.
    Includes the FULL token on purpose — this is only ever served over loopback."""
    token = get_or_create_token()
    pairing_urls = phone_pairing_urls(token)
    return {
        "report_kind": REPORT_KIND,
        "owner_token": token,
        "token_hint": mask_token(token),
        "lan_mode_enabled": lan_mode_enabled(),
        "header_name": "X-CAS-Owner-Token",
        "pairing_hash_key": PAIRING_HASH_KEY,
        "api_base_hash_key": API_BASE_HASH_KEY,
        "pairing_urls": pairing_urls,
        "native_pairing_urls": phone_native_pairing_urls(token),
        "pairing_api_bases": phone_pairing_api_bases(),
        "direct_api_bases": phone_direct_api_bases(),
        "how_to_pair": (
            "On the other device, open one of the pairing URLs or enter this "
            "token when asked. Turn LAN mode ON here to allow it in."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def phone_pairing_urls(token: str, *, port: int | None = None) -> list[str]:
    """Return phone-openable LAN URLs carrying pairing state in the fragment."""
    from urllib.parse import urlencode

    web_port = int(port or os.environ.get("CAS_FOREX_PHONE_WEB_PORT") or DEFAULT_PHONE_WEB_PORT)
    hosts = _local_lan_hosts()
    return [
        f"http://{host}:{web_port}/?page=quick-start#"
        f"{urlencode({PAIRING_HASH_KEY: str(token), API_BASE_HASH_KEY: _pairing_api_base(host, web_port)})}"
        for host in hosts
    ]


def phone_pairing_api_bases(*, port: int | None = None) -> list[str]:
    """API bases reachable from the phone through the installable web/PWA proxy."""
    web_port = int(port or os.environ.get("CAS_FOREX_PHONE_WEB_PORT") or DEFAULT_PHONE_WEB_PORT)
    return [_pairing_api_base(host, web_port) for host in _local_lan_hosts()]


def phone_direct_api_bases(*, port: int | None = None) -> list[str]:
    """Direct API bases for APK/dev-server setups that intentionally expose 8765."""
    api_port = int(port or os.environ.get("CAS_FOREX_PHONE_API_PORT") or DEFAULT_PHONE_API_PORT)
    return [f"http://{host}:{api_port}/api/forex" for host in _local_lan_hosts()]


def phone_native_pairing_urls(token: str, *, port: int | None = None) -> list[str]:
    """Android app deep links that carry the owner token and direct API base."""
    from urllib.parse import urlencode

    direct_bases = phone_direct_api_bases(port=port)
    return [
        f"{NATIVE_PAIRING_SCHEME}://pair?"
        f"{urlencode({PAIRING_HASH_KEY: str(token), API_BASE_HASH_KEY: api_base, 'page': 'quick-start'})}"
        for api_base in direct_bases
    ]


def _pairing_api_base(host: str, port: int) -> str:
    return f"http://{host}:{port}/api/forex"


def _local_lan_hosts() -> tuple[str, ...]:
    explicit = os.environ.get("CAS_FOREX_LAN_HOST")
    explicit_hosts: list[str] = []
    discovered_hosts: list[str] = []
    if explicit:
        explicit_hosts.extend(part.strip() for part in explicit.split(",") if part.strip())
    try:
        _, _, addresses = socket.gethostbyname_ex(socket.gethostname())
        discovered_hosts.extend(addresses)
    except OSError:
        pass

    out: list[str] = []
    for host in explicit_hosts:
        if _is_usable_lan_ipv4(host) and host not in out:
            out.append(host)
    ranked_discovered = sorted(
        (host for host in discovered_hosts if _is_usable_lan_ipv4(host)),
        key=_lan_host_rank,
    )
    for host in ranked_discovered:
        if host not in out:
            out.append(host)
    return tuple(out)


def _lan_host_rank(host: str) -> tuple[int, str]:
    address = ipaddress.ip_address(host)
    if address in ipaddress.ip_network("10.0.0.0/8") or address in ipaddress.ip_network("192.168.0.0/16"):
        return (0, host)
    if address.is_private:
        return (1, host)
    return (2, host)


def _is_usable_lan_ipv4(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.version == 4
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_unspecified
    )


__all__ = [
    "CLAIM_BOUNDARY",
    "AuthDecision",
    "PAIRING_HASH_KEY",
    "auth_store_status",
    "current_token",
    "effective_client_host",
    "evaluate_request",
    "extract_forwarded_client_host",
    "extract_token",
    "get_or_create_token",
    "lan_mode_enabled",
    "mask_token",
    "pairing_payload",
    "phone_pairing_urls",
    "request_is_loopback",
    "rotate_token",
    "set_auth_path_for_tests",
    "set_lan_mode",
    "verify_token",
]
