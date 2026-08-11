"""Shared phone-facing web URL helpers for CAS Forex mobile workflows."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

DEFAULT_PHONE_WEB_PORT = 4173


def default_mobile_web_base(port: int = DEFAULT_PHONE_WEB_PORT) -> str:
    """Return the best phone-openable web base, falling back to loopback."""
    try:
        from cas_forex.owner_auth import phone_pairing_api_bases

        bases = phone_pairing_api_bases(port=port)
        if bases:
            parsed = urlsplit(bases[0])
            if parsed.scheme and parsed.netloc:
                return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    except Exception:
        pass
    return f"http://127.0.0.1:{int(port or DEFAULT_PHONE_WEB_PORT)}"


def quick_start_url(web_base: str | None) -> str:
    """Return the Quick Start URL for a base origin or an already-expanded URL."""
    base = str(web_base or "").strip().rstrip("/")
    if not base:
        base = default_mobile_web_base()
    if "?page=quick-start" in base:
        return base
    return f"{base}/?page=quick-start"
