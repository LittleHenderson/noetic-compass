"""Local, durable secret store for the AI operator (owner's machine only).

The owner can paste a Claude API key into the app; it is written here so it
survives restarts. The file lives under ``runtime/`` which is git-ignored, so
the key is never committed. Values are NEVER logged or echoed back — callers
get only a masked presence flag.

This is a single-owner local convenience store, not a vault: the key sits in a
plaintext JSON on the owner's own disk (same trust level as a .env file). Prefer
an OS keychain / env var for shared or server deployments.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SECRETS_PATH = REPO_ROOT / "runtime" / "operator-secrets.json"

_LOCK = threading.RLock()
_PATH = DEFAULT_SECRETS_PATH


def set_secrets_path_for_tests(path: Optional[Path]) -> None:
    global _PATH
    _PATH = Path(path) if path is not None else DEFAULT_SECRETS_PATH


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


def mask(value: Optional[str]) -> str:
    """A safe display form: presence + last 4 chars, never the full secret."""
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 4 else "****"
    return f"…{tail}"
