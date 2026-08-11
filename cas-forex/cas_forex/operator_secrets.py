"""Local, durable encrypted secret store for the AI operator.

The owner can paste Claude or DeepSeek API keys into the app; they are written here so they
survives restarts. The file lives under ``runtime/`` which is git-ignored, so
the key is never committed. Values are NEVER logged or echoed back — callers
get only a masked presence flag.

Secret values are stored as local encrypted envelopes and are never returned by
API reports. Static env/config keys remain a fallback for deployments that
prefer external secret management.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

from cas_forex.secret_envelope import (
    is_secret_envelope,
    protect_secret,
    secret_storage_status,
    unprotect_secret,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS_PATH = REPO_ROOT / "runtime" / "operator-secrets.json"
REPORT_KIND = "cas_forex_operator_secrets"

_LOCK = threading.RLock()
_PATH = DEFAULT_SECRETS_PATH


def set_secrets_path_for_tests(path: Optional[Path]) -> None:
    global _PATH
    _PATH = Path(path) if path is not None else DEFAULT_SECRETS_PATH


def _load() -> dict[str, str]:
    if not _PATH.exists():
        return {}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    raw = data.get("secrets") if data.get("report_kind") == REPORT_KIND else data
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    migrated_plaintext = False
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name or value is None:
            continue
        try:
            secret = unprotect_secret(value)
        except Exception:
            continue
        if secret:
            out[name] = secret
            if not is_secret_envelope(value):
                migrated_plaintext = True
    if migrated_plaintext:
        _save(out)
    return out


def _save(data: dict[str, str]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(_PATH.suffix + ".tmp")
    encrypted = {
        str(key): protect_secret(str(value))
        for key, value in data.items()
        if str(key).strip() and str(value or "").strip()
    }
    payload = json.dumps(
        {
            "report_kind": REPORT_KIND,
            "secrets": encrypted,
            "secret_storage": secret_storage_status(),
            "claim_boundary": (
                "Local AI-operator secret store. Values are stored as local "
                "encrypted envelopes and are never returned by API reports."
            ),
        },
        indent=2,
        sort_keys=True,
    )
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


def get_secret(name: str) -> Optional[str]:
    with _LOCK:
        value = _load().get(name)
        return str(value) if value else None


def set_secret(name: str, value: Optional[str]) -> None:
    """Set (or, with a falsy value, clear) a secret. Never logs the value."""
    with _LOCK:
        data = _load()
        if value:
            data[name] = str(value)
        else:
            data.pop(name, None)
        _save(data)


def store_status() -> dict[str, Any]:
    """Read-only storage metadata. Does not reveal secret names or values."""
    storage = dict(secret_storage_status())
    return {
        "path": str(_PATH),
        "report_kind": REPORT_KIND,
        "at_rest_encrypted": bool(storage.get("at_rest_encrypted")),
        "secret_storage": storage,
    }


def mask(value: Optional[str]) -> str:
    """A safe display form: presence + last 4 chars, never the full secret."""
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 4 else "****"
    return f"…{tail}"
