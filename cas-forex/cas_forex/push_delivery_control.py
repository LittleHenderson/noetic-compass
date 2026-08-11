"""Owner/runtime control for Web Push delivery configuration.

This module resolves the server-side VAPID material used for browser push
subscriptions and off-screen push delivery. The public key is inspectable so
the browser can subscribe; the private key stays server-side and is encrypted
at rest when stored as a runtime override.
"""

from __future__ import annotations

import json
import os
import threading
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import urlsplit

from cas_forex.secret_envelope import (
    is_secret_envelope,
    protect_secret,
    secret_storage_status,
    unprotect_secret,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDE_PATH = REPO_ROOT / "runtime" / "push-delivery-overrides.json"
REPORT_KIND = "cas_forex_push_delivery_backend"

VAPID_PUBLIC_KEY = "vapid_public_key"
VAPID_PRIVATE_KEY = "vapid_private_key"
VAPID_SUBJECT = "vapid_subject"

PUBLIC_KEY_ENV_KEYS = (
    "CAS_FOREX_VAPID_PUBLIC_KEY",
    "VAPID_PUBLIC_KEY",
    "VITE_CAS_FOREX_VAPID_PUBLIC_KEY",
)
PRIVATE_KEY_ENV_KEYS = (
    "CAS_FOREX_VAPID_PRIVATE_KEY",
    "VAPID_PRIVATE_KEY",
)
SUBJECT_ENV_KEYS = (
    "CAS_FOREX_VAPID_SUBJECT",
    "VAPID_SUBJECT",
)

_ALL_KEYS = (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT)
_UNSET = object()

_LOCK = threading.RLock()
_PATH = DEFAULT_OVERRIDE_PATH
_OVERRIDES_LOADED = False
_OVERRIDES: dict[str, str] = {}

CLAIM_BOUNDARY = (
    "Push delivery backend reports only Web Push transport readiness and "
    "VAPID configuration presence for observational browser notifications. "
    "The VAPID private key remains server-side and masked in reports. This "
    "does not authorize trading, move money, or emit advisory trade picks."
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
        "secret_keys": list(_ALL_KEYS),
        "secret_storage": secret_storage_status(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_PATH)


def _mask_value(value: str, *, value_kind: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    if value_kind == "public_key":
        if len(cleaned) <= 16:
            return "configured-public-key"
        return f"{cleaned[:8]}...{cleaned[-8:]}"
    if value_kind == "url":
        parsed = urlsplit(cleaned)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/..."
        return "configured-url-redacted"
    if value_kind == "subject":
        if cleaned.startswith("mailto:") and "@" in cleaned:
            local, _, domain = cleaned[7:].partition("@")
            if local:
                return f"mailto:{local[:2]}...@{domain or '...'}"
        parsed = urlsplit(cleaned)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/..."
        return "configured-subject-redacted"
    if len(cleaned) <= 8:
        return "configured-secret-redacted"
    return f"{cleaned[:4]}...{cleaned[-4:]}"


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
            "masked_value": _mask_value(runtime_value, value_kind=value_kind),
            "source": "runtime_override",
        }
    for env_key in env_keys:
        env_value = str(env_map.get(env_key, "") or "").strip()
        if env_value:
            return {
                "configured": True,
                "value": env_value,
                "configured_key": env_key,
                "masked_value": _mask_value(env_value, value_kind=value_kind),
                "source": "env",
            }
    return {
        "configured": False,
        "value": "",
        "configured_key": None,
        "masked_value": None,
        "source": "unset",
    }


def resolve_push_delivery_config(
    env: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    env_map = dict(os.environ if env is None else env)
    with _LOCK:
        _load_overrides()
        runtime = dict(_OVERRIDES)
    return {
        VAPID_PUBLIC_KEY: _resolve_value(
            key=VAPID_PUBLIC_KEY,
            env_keys=PUBLIC_KEY_ENV_KEYS,
            env_map=env_map,
            runtime=runtime,
            value_kind="public_key",
        ),
        VAPID_PRIVATE_KEY: _resolve_value(
            key=VAPID_PRIVATE_KEY,
            env_keys=PRIVATE_KEY_ENV_KEYS,
            env_map=env_map,
            runtime=runtime,
            value_kind="secret",
        ),
        VAPID_SUBJECT: _resolve_value(
            key=VAPID_SUBJECT,
            env_keys=SUBJECT_ENV_KEYS,
            env_map=env_map,
            runtime=runtime,
            value_kind="subject",
        ),
    }


def probe_push_delivery_backend() -> dict[str, Any]:
    try:
        import_module("pywebpush")
    except Exception:
        return {
            "available": False,
            "package": "pywebpush",
            "version": None,
        }
    try:
        detected_version = package_version("pywebpush")
    except PackageNotFoundError:
        detected_version = None
    return {
        "available": True,
        "package": "pywebpush",
        "version": detected_version,
    }


def build_push_delivery_backend_report(
    env: Mapping[str, str] | None = None,
    *,
    subscription_count: int = 0,
) -> dict[str, Any]:
    resolved = resolve_push_delivery_config(env)
    backend = probe_push_delivery_backend()
    public_key = resolved[VAPID_PUBLIC_KEY]
    private_key = resolved[VAPID_PRIVATE_KEY]
    subject = resolved[VAPID_SUBJECT]

    browser_subscriptions_present = subscription_count > 0
    subscription_registration_ready = bool(public_key["configured"])
    dispatch_ready = bool(
        backend["available"] and private_key["configured"] and subject["configured"]
    )
    fully_ready = bool(subscription_registration_ready and dispatch_ready)

    blockers: list[str] = []
    if not backend["available"]:
        blockers.append("Install pywebpush in the API environment.")
    if not public_key["configured"]:
        blockers.append("Configure a VAPID public key for browser subscription creation.")
    if not private_key["configured"]:
        blockers.append("Configure a server-side VAPID private key for push delivery.")
    if not subject["configured"]:
        blockers.append("Configure a VAPID subject (mailto:... or https://...).")
    if not browser_subscriptions_present:
        blockers.append("No browser push subscriptions are registered yet.")

    if fully_ready and browser_subscriptions_present:
        status = "READY"
        next_action = "Push delivery is ready. Send a test push to verify end-to-end delivery."
    elif dispatch_ready and subscription_registration_ready:
        status = "READY_NO_SUBSCRIPTIONS"
        next_action = "Push backend is ready. Register a browser subscription, then send a test push."
    elif backend["available"]:
        status = "CONFIG_NEEDED"
        next_action = "Complete the missing VAPID fields, then register a browser subscription."
    else:
        status = "BACKEND_MISSING"
        next_action = "Install pywebpush, configure VAPID keys, then register a browser subscription."

    return {
        "report_kind": REPORT_KIND,
        "status": status,
        "dispatch_backend_available": bool(backend["available"]),
        "dispatch_backend_package": backend["package"],
        "dispatch_backend_version": backend["version"],
        "subscription_count": int(max(subscription_count, 0)),
        "browser_subscriptions_present": browser_subscriptions_present,
        "subscription_registration_ready": subscription_registration_ready,
        "dispatch_ready": dispatch_ready,
        "fully_ready": fully_ready,
        "blockers": blockers,
        "next_action": next_action,
        "vapid_public_key": str(public_key["value"] or ""),
        "vapid_public_key_configured": bool(public_key["configured"]),
        "vapid_public_key_configured_key": public_key["configured_key"],
        "vapid_public_key_source": public_key["source"],
        "vapid_public_key_masked": public_key["masked_value"],
        "vapid_private_key": {
            "configured": bool(private_key["configured"]),
            "configured_key": private_key["configured_key"],
            "masked_value": private_key["masked_value"],
            "source": private_key["source"],
            "env_keys": list(PRIVATE_KEY_ENV_KEYS),
        },
        "vapid_subject": {
            "configured": bool(subject["configured"]),
            "value": str(subject["value"] or ""),
            "configured_key": subject["configured_key"],
            "masked_value": subject["masked_value"],
            "source": subject["source"],
            "env_keys": list(SUBJECT_ENV_KEYS),
        },
        "runtime_override_path": str(_PATH),
        "secret_storage": dict(secret_storage_status()),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def set_push_delivery_overrides(
    *,
    vapid_public_key: Any = _UNSET,
    vapid_private_key: Any = _UNSET,
    vapid_subject: Any = _UNSET,
) -> list[str]:
    changed: list[str] = []
    with _LOCK:
        _load_overrides()
        for key, value in (
            (VAPID_PUBLIC_KEY, vapid_public_key),
            (VAPID_PRIVATE_KEY, vapid_private_key),
            (VAPID_SUBJECT, vapid_subject),
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


def clear_push_delivery_overrides() -> list[str]:
    with _LOCK:
        _load_overrides()
        changed = sorted(_OVERRIDES.keys())
        _OVERRIDES.clear()
        _save_overrides()
    return changed


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_OVERRIDE_PATH",
    "PRIVATE_KEY_ENV_KEYS",
    "PUBLIC_KEY_ENV_KEYS",
    "REPORT_KIND",
    "SUBJECT_ENV_KEYS",
    "VAPID_PRIVATE_KEY",
    "VAPID_PUBLIC_KEY",
    "VAPID_SUBJECT",
    "build_push_delivery_backend_report",
    "clear_push_delivery_overrides",
    "probe_push_delivery_backend",
    "resolve_push_delivery_config",
    "set_override_path_for_tests",
    "set_push_delivery_overrides",
]
