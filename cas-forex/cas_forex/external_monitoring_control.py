"""Owner-configurable runtime overrides for external monitoring hooks.

Hosted uptime heartbeat URLs, error-tracking DSNs, and off-screen alert
webhooks should not require manual `.env` edits on the owner's machine. This
module provides the same single-owner runtime-override pattern already used for
other operational controls, while keeping the values server-side and encrypted
at rest.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex.secret_envelope import (
    is_secret_envelope,
    protect_secret,
    secret_storage_status,
    unprotect_secret,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDE_PATH = REPO_ROOT / "runtime" / "external-monitoring-overrides.json"
REPORT_KIND = "cas_forex_external_monitoring_control"

UPTIME_MONITOR_URL_KEY = "uptime_monitor_url"
ERROR_TRACKING_DSN_KEY = "error_tracking_dsn"
ALERT_WEBHOOK_URL_KEY = "alert_webhook_url"

UPTIME_ENV_KEYS = (
    "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL",
    "CAS_FOREX_UPTIME_MONITOR_URL",
    "CAS_FOREX_HEALTHCHECKS_PING_URL",
    "HEALTHCHECKS_PING_URL",
)
ERROR_TRACKING_ENV_KEYS = (
    "CAS_FOREX_ERROR_TRACKING_DSN",
    "SENTRY_DSN",
)
ALERT_WEBHOOK_ENV_KEYS = (
    "CAS_FOREX_ALERT_WEBHOOK_URL",
    "CAS_FOREX_CRITICAL_WEBHOOK_URL",
    "CAS_FOREX_WEBHOOK_NOTIFICATION_URL",
)

_ALL_KEYS = (UPTIME_MONITOR_URL_KEY, ERROR_TRACKING_DSN_KEY, ALERT_WEBHOOK_URL_KEY)
_SECRET_KEYS = frozenset(_ALL_KEYS)
_UNSET = object()

_LOCK = threading.RLock()
_PATH = DEFAULT_OVERRIDE_PATH
_OVERRIDES_LOADED = False
_OVERRIDES: dict[str, str] = {}

CLAIM_BOUNDARY = (
    "External monitoring control stores owner-supplied uptime, error-tracking, "
    "and alert-delivery hooks for the local cockpit runtime. Values are masked "
    "in reports, kept server-side, and do not ping external services, place "
    "orders, move money, or authorize live trading."
)


def set_override_path_for_tests(path: Optional[Path]) -> None:
    global _PATH, _OVERRIDES_LOADED
    with _LOCK:
        _PATH = Path(path) if path is not None else DEFAULT_OVERRIDE_PATH
        _OVERRIDES.clear()
        _OVERRIDES_LOADED = False


def _load_overrides() -> None:
    global _OVERRIDES_LOADED
    if _OVERRIDES_LOADED:
        return
    _OVERRIDES_LOADED = True
    if _PATH is None or not _PATH.exists():
        return
    try:
        payload = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    raw = payload.get("overrides") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return
    migrated_plaintext = False
    for key, value in raw.items():
        name = str(key or "").strip()
        if name not in _ALL_KEYS or value is None:
            continue
        try:
            resolved = unprotect_secret(value).strip()
        except Exception:
            continue
        if not resolved:
            continue
        _OVERRIDES[name] = resolved
        if not is_secret_envelope(value):
            migrated_plaintext = True
    if migrated_plaintext:
        _save_overrides()


def _save_overrides() -> None:
    if _PATH is None:
        return
    if not _OVERRIDES:
        try:
            _PATH.unlink()
        except FileNotFoundError:
            pass
        return
    payload = {
        "report_kind": REPORT_KIND,
        "overrides": {
            key: protect_secret(value)
            for key, value in _OVERRIDES.items()
            if key in _ALL_KEYS and str(value or "").strip()
        },
        "secret_keys": sorted(_SECRET_KEYS),
        "secret_storage": secret_storage_status(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_PATH)


def _masked_value(value: str, *, value_kind: str) -> str:
    if not value:
        return ""
    if value_kind == "url":
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/..."
        return "configured-url-redacted"
    if len(value) <= 8:
        return "configured-secret-redacted"
    return f"{value[:4]}...{value[-4:]}"


def resolve_external_monitoring_config(
    env: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    env_map = dict(os.environ if env is None else env)
    with _LOCK:
        _load_overrides()
        runtime = dict(_OVERRIDES)
    return {
        UPTIME_MONITOR_URL_KEY: _resolve_value(
            key=UPTIME_MONITOR_URL_KEY,
            env_keys=UPTIME_ENV_KEYS,
            env_map=env_map,
            runtime=runtime,
            value_kind="url",
        ),
        ERROR_TRACKING_DSN_KEY: _resolve_value(
            key=ERROR_TRACKING_DSN_KEY,
            env_keys=ERROR_TRACKING_ENV_KEYS,
            env_map=env_map,
            runtime=runtime,
            value_kind="secret",
        ),
        ALERT_WEBHOOK_URL_KEY: _resolve_value(
            key=ALERT_WEBHOOK_URL_KEY,
            env_keys=ALERT_WEBHOOK_ENV_KEYS,
            env_map=env_map,
            runtime=runtime,
            value_kind="url",
        ),
    }


def _resolve_value(
    *,
    key: str,
    env_keys: tuple[str, ...],
    env_map: Mapping[str, str],
    runtime: Mapping[str, str],
    value_kind: str,
) -> dict[str, Any]:
    runtime_value = str(runtime.get(key) or "").strip()
    if runtime_value:
        return {
            "configured": True,
            "value": runtime_value,
            "configured_key": "runtime_override",
            "masked_value": _masked_value(runtime_value, value_kind=value_kind),
            "source": "runtime_override",
        }
    for env_key in env_keys:
        probe = str(env_map.get(env_key, "") or "").strip()
        if probe:
            return {
                "configured": True,
                "value": probe,
                "configured_key": env_key,
                "masked_value": _masked_value(probe, value_kind=value_kind),
                "source": "env",
            }
    return {
        "configured": False,
        "value": "",
        "configured_key": None,
        "masked_value": None,
        "source": "unset",
    }


def build_external_monitoring_control_report(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    resolved = resolve_external_monitoring_config(env)
    storage = dict(secret_storage_status())
    return {
        "report_kind": REPORT_KIND,
        "status": "OK",
        "uptime_monitor": {
            "configured": bool(resolved[UPTIME_MONITOR_URL_KEY]["configured"]),
            "configured_key": resolved[UPTIME_MONITOR_URL_KEY]["configured_key"],
            "masked_value": resolved[UPTIME_MONITOR_URL_KEY]["masked_value"],
            "env_keys": list(UPTIME_ENV_KEYS),
        },
        "error_tracking_dsn": {
            "configured": bool(resolved[ERROR_TRACKING_DSN_KEY]["configured"]),
            "configured_key": resolved[ERROR_TRACKING_DSN_KEY]["configured_key"],
            "masked_value": resolved[ERROR_TRACKING_DSN_KEY]["masked_value"],
            "env_keys": list(ERROR_TRACKING_ENV_KEYS),
        },
        "alert_destination": {
            "configured": bool(resolved[ALERT_WEBHOOK_URL_KEY]["configured"]),
            "configured_key": resolved[ALERT_WEBHOOK_URL_KEY]["configured_key"],
            "masked_value": resolved[ALERT_WEBHOOK_URL_KEY]["masked_value"],
            "env_keys": list(ALERT_WEBHOOK_ENV_KEYS),
        },
        "runtime_override_path": str(_PATH),
        "secret_storage": storage,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def set_external_monitoring_overrides(
    *,
    uptime_monitor_url: Any = _UNSET,
    error_tracking_dsn: Any = _UNSET,
    alert_webhook_url: Any = _UNSET,
) -> list[str]:
    changed: list[str] = []
    with _LOCK:
        _load_overrides()
        for key, value in (
            (UPTIME_MONITOR_URL_KEY, uptime_monitor_url),
            (ERROR_TRACKING_DSN_KEY, error_tracking_dsn),
            (ALERT_WEBHOOK_URL_KEY, alert_webhook_url),
        ):
            if value is _UNSET:
                continue
            cleaned = str(value or "").strip()
            previous = str(_OVERRIDES.get(key) or "").strip()
            if cleaned:
                if previous != cleaned:
                    _OVERRIDES[key] = cleaned
                    changed.append(key)
            elif key in _OVERRIDES:
                _OVERRIDES.pop(key, None)
                changed.append(key)
        _save_overrides()
    return changed


def clear_external_monitoring_overrides() -> list[str]:
    with _LOCK:
        _load_overrides()
        changed = sorted(_OVERRIDES.keys())
        _OVERRIDES.clear()
        _save_overrides()
    return changed


__all__ = [
    "ALERT_WEBHOOK_ENV_KEYS",
    "ALERT_WEBHOOK_URL_KEY",
    "ERROR_TRACKING_DSN_KEY",
    "ERROR_TRACKING_ENV_KEYS",
    "REPORT_KIND",
    "UPTIME_ENV_KEYS",
    "UPTIME_MONITOR_URL_KEY",
    "build_external_monitoring_control_report",
    "clear_external_monitoring_overrides",
    "resolve_external_monitoring_config",
    "set_external_monitoring_overrides",
    "set_override_path_for_tests",
]
