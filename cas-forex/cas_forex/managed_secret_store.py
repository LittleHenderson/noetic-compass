"""Managed secret-store readiness for CAS Forex.

CAS Forex uses local encrypted envelopes today. On Windows those envelopes are
protected by DPAPI, which is an OS-managed current-user secret boundary. This
module reports that posture explicitly and exposes the deployment gap that
would remain in cloud/public hosting without an external secrets manager.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
from typing import Any

from cas_forex.secret_envelope import secret_storage_status


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_managed_secret_store"
CLAIM_BOUNDARY = (
    "Managed secret-store readiness is a read-only security report. It checks "
    "whether CAS Forex has an OS/current-user or externally managed place for "
    "server-side secrets. It does not return raw secrets, change credentials, "
    "place orders, move money, or authorize live trading."
)


def build_managed_secret_store_report(config: Any = None) -> dict[str, Any]:
    cfg = _resolve_config(config)
    cloud_mode = _env_bool("CAS_FOREX_CLOUD_MODE", False)
    requested_backend = str(getattr(cfg, "secret_store_backend", "") or os.environ.get("CAS_FOREX_SECRET_STORE_BACKEND", "auto"))
    external_provider = str(
        getattr(cfg, "secret_manager_provider", "")
        or os.environ.get("CAS_FOREX_SECRET_MANAGER_PROVIDER", "")
    ).strip()
    external_configured = bool(
        getattr(cfg, "secret_manager_configured", False)
        or _env_bool("CAS_FOREX_SECRET_MANAGER_CONFIGURED", False)
        or external_provider
    )
    envelope = dict(secret_storage_status())
    os_current_user = _os_current_user_secret_status()
    credential_manager = _windows_credential_manager_status()

    if external_configured:
        backend_status = "EXTERNAL_MANAGED_STORE_CONFIGURED"
        status = "OK"
        backend = external_provider or "external_secret_manager"
        detail = "External managed secret-manager configuration is present."
    elif os_current_user.get("available"):
        backend_status = "OS_MANAGED_CURRENT_USER"
        backend = str(os_current_user.get("provider") or envelope.get("scheme") or "os_current_user")
        status = "ATTENTION" if cloud_mode else "OK"
        detail = (
            "Windows DPAPI/current-user protection is available for the local desktop runtime."
            if not cloud_mode
            else "Cloud mode is on; local OS-current-user protection is not a substitute for a hosted secrets manager."
        )
    elif envelope.get("at_rest_encrypted"):
        backend_status = "LOCAL_ENCRYPTED_ENVELOPE"
        backend = str(envelope.get("scheme") or "local_envelope")
        status = "ATTENTION" if cloud_mode else "OK"
        detail = (
            "Local encrypted envelope storage is available; use an external managed store before hosted deployment."
            if cloud_mode
            else "Local encrypted envelope storage is available for this single-owner desktop runtime."
        )
    else:
        backend_status = "NO_MANAGED_STORE"
        backend = ""
        status = "ATTENTION"
        detail = "No encrypted or managed secret-store backend is available."

    attention: list[str] = []
    if cloud_mode and not external_configured:
        attention.append("Cloud/public mode requires an external managed secrets manager.")
    if requested_backend.lower() not in {"", "auto", backend.lower()} and requested_backend.lower() != "local_envelope":
        attention.append(f"Requested secret backend '{requested_backend}' is not the active backend '{backend}'.")
    if not envelope.get("at_rest_encrypted"):
        attention.append("Runtime secret envelopes do not report at-rest encryption.")

    return {
        "report_kind": REPORT_KIND,
        "status": "ATTENTION" if attention else status,
        "backend_status": backend_status,
        "active_backend": backend,
        "requested_backend": requested_backend,
        "cloud_mode": cloud_mode,
        "external_secret_manager": {
            "configured": external_configured,
            "provider": external_provider,
            "provider_set": bool(external_provider),
        },
        "os_current_user_store": os_current_user,
        "windows_credential_manager": credential_manager,
        "runtime_secret_envelope": envelope,
        "server_side_only": True,
        "raw_secret_returned": False,
        "attention_items": attention,
        "detail": detail,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _resolve_config(config: Any = None) -> Any:
    if config is not None:
        return config
    from cas_forex.config import config as default_config

    return default_config


def _os_current_user_secret_status() -> dict[str, Any]:
    if os.name == "nt":
        return {
            "available": _dpapi_available(),
            "provider": "windows_dpapi_current_user",
            "scope": "current_windows_user",
            "portable_between_users": False,
            "portable_to_cloud": False,
        }
    return {
        "available": False,
        "provider": "",
        "scope": "not_available",
        "portable_between_users": False,
        "portable_to_cloud": False,
    }


def _dpapi_available() -> bool:
    if os.name != "nt":
        return False
    try:
        ctypes.windll.crypt32  # type: ignore[attr-defined]
        ctypes.windll.kernel32  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def _windows_credential_manager_status() -> dict[str, Any]:
    if os.name != "nt":
        return {
            "available": False,
            "provider": "",
            "detail": "Windows Credential Manager is available only on Windows.",
        }
    try:
        ctypes.windll.advapi32.CredReadW  # type: ignore[attr-defined]
        ctypes.windll.advapi32.CredWriteW  # type: ignore[attr-defined]
        ctypes.windll.advapi32.CredFree  # type: ignore[attr-defined]
        return {
            "available": True,
            "provider": "windows_credential_manager",
            "scope": "current_windows_user",
            "detail": "Windows Credential Manager APIs are available.",
        }
    except Exception as exc:
        return {
            "available": False,
            "provider": "windows_credential_manager",
            "detail": f"Windows Credential Manager APIs are unavailable: {type(exc).__name__}: {exc}",
        }


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
