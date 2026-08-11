"""Exact configured-vs-connected MT5 account identity checks.

The terminal can safely retain the trading password, but CAS must still prove
that the account currently visible through MT5 is the configured owner account.
Only login and server identity are handled here; no credential is read or
returned.
"""

from __future__ import annotations

from typing import Any, Mapping


def normalize_mt5_login(value: Any) -> int | None:
    try:
        login = int(value)
    except (TypeError, ValueError):
        return None
    return login if login > 0 else None


def normalize_mt5_server(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def configured_mt5_account_identity(config: Any = None) -> dict[str, Any]:
    if config is None:
        from cas_forex.config import config as runtime_config

        config = runtime_config
    login = normalize_mt5_login(getattr(config, "mt5_login", 0))
    server = str(getattr(config, "mt5_server", "") or "").strip()
    return {
        "login": login,
        "server": server,
        "complete": bool(login and normalize_mt5_server(server)),
    }


def evaluate_mt5_account_identity(
    snapshot: Mapping[str, Any],
    *,
    config: Any = None,
) -> dict[str, Any]:
    """Compare connected MT5 identity with trusted CAS configuration.

    The broker snapshot is evidence about the connected account. It must never
    be allowed to declare the account identity it is expected to match.
    """

    configured_identity = configured_mt5_account_identity(config)
    expected_login = configured_identity["login"]
    expected_server = configured_identity["server"]

    account = snapshot.get("account") if isinstance(snapshot.get("account"), Mapping) else {}
    actual_login = normalize_mt5_login(account.get("login"))
    actual_server = str(account.get("server") or "").strip()
    expected_server_normalized = normalize_mt5_server(expected_server)
    actual_server_normalized = normalize_mt5_server(actual_server)
    configured = bool(expected_login and expected_server_normalized)
    observable = bool(
        snapshot.get("connected") is True
        and actual_login
        and actual_server_normalized
    )

    mismatch_fields: list[str] = []
    if configured and observable:
        if actual_login != expected_login:
            mismatch_fields.append("login")
        if actual_server_normalized != expected_server_normalized:
            mismatch_fields.append("server")
        matches: bool | None = not mismatch_fields
    else:
        matches = None

    return {
        "configured": configured,
        "observable": observable,
        "matches": matches,
        "expected_login": expected_login,
        "expected_server": expected_server or None,
        "actual_login": actual_login,
        "actual_server": actual_server or None,
        "mismatch_fields": mismatch_fields,
    }


__all__ = [
    "configured_mt5_account_identity",
    "evaluate_mt5_account_identity",
    "normalize_mt5_login",
    "normalize_mt5_server",
]
