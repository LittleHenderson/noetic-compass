"""In-memory assessment store keyed by API key.

Thread-safe, max 1000 records per key. Resets on server restart.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_MAX_RECORDS_PER_KEY = 1000

_lock = threading.Lock()
_store: dict[str, list[dict[str, Any]]] = defaultdict(list)


def save_assessment(api_key: str, text: str, response: dict[str, Any]) -> None:
    """Append an assessment record for the given API key."""
    record = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "text": text,
        "response": response,
    }
    with _lock:
        bucket = _store[api_key]
        bucket.append(record)
        if len(bucket) > _MAX_RECORDS_PER_KEY:
            _store[api_key] = bucket[-_MAX_RECORDS_PER_KEY:]


def get_assessments(api_key: str) -> list[dict[str, Any]]:
    """Return all stored assessments for the given API key."""
    with _lock:
        return list(_store[api_key])


def clear_assessments(api_key: str | None = None) -> None:
    """Clear stored assessments. If api_key is None, clear all."""
    with _lock:
        if api_key is None:
            _store.clear()
        else:
            _store.pop(api_key, None)
