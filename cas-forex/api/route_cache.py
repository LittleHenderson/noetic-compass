"""Tiny cache-first wrapper for expensive read-only API packets."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Mapping


Builder = Callable[[], dict[str, Any]]

_LOCK = threading.RLock()
_CACHES: dict[str, dict[str, Any]] = {}
_REFRESH_SEMAPHORE = threading.Semaphore(1)


def under_pytest() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def invalidate_cache(*keys: str) -> None:
    """Drop cache-first packets after owner writes change their gate inputs.

    With no keys, this clears every packet. Passing explicit keys keeps hot
    polling caches stable while making the changed authorization/money packets
    rebuild on the next read.
    """

    with _LOCK:
        if not keys:
            _CACHES.clear()
            return
        for key in keys:
            _CACHES.pop(key, None)


def store_cache_payload(key: str, payload: Mapping[str, Any]) -> None:
    """Seed a cache-first packet after a synchronous rebuild.

    This is used after broker-affecting actions so the next dashboard read can
    observe the freshly rebuilt packet instead of waiting for the normal
    background warmer.
    """

    with _LOCK:
        _CACHES[key] = {
            "payload": dict(payload),
            "built_at": time.time(),
            "building": False,
            "error": None,
            "refresh_started_at": 0.0,
        }


def cached_payload_snapshot(key: str, *, ttl_seconds: float = 60.0) -> dict[str, Any] | None:
    """Return the latest cached packet without starting a refresh."""

    now = time.time()
    with _LOCK:
        cache = _CACHES.get(key)
        if not isinstance(cache, dict):
            return None
        payload = cache.get("payload")
        if not isinstance(payload, dict):
            return None
        built_at = float(cache.get("built_at") or 0.0)
        building = bool(cache.get("building"))
        error = cache.get("error")
    age = now - built_at if built_at else None
    status = "fresh" if age is not None and age <= ttl_seconds else "stale"
    if building:
        status = "refreshing"
    return _with_cache_meta(dict(payload), status, built_at or None, ttl_seconds, error)


def cache_first_payload(
    key: str,
    *,
    builder: Builder,
    fallback: Builder,
    ttl_seconds: float = 60.0,
    block_on_cold: bool = False,
    serialize_refresh: bool = True,
) -> dict[str, Any]:
    """Return cached packet immediately and refresh expensive builders off-loop."""
    if under_pytest():
        return builder()

    now = time.time()
    with _LOCK:
        cache = _CACHES.setdefault(
            key,
            {"payload": None, "built_at": 0.0, "building": False, "error": None, "refresh_started_at": 0.0},
        )
        payload = cache.get("payload")
        built_at = float(cache.get("built_at") or 0.0)
        building = bool(cache.get("building"))
        fresh = isinstance(payload, dict) and (now - built_at) <= ttl_seconds

    if fresh and isinstance(payload, dict):
        return _with_cache_meta(payload, "fresh", built_at, ttl_seconds, None)

    if block_on_cold and not isinstance(payload, dict) and not building:
        try:
            payload = run_serial_refresh(builder) if serialize_refresh else builder()
            if not isinstance(payload, dict):
                payload = {"status": "UNAVAILABLE", "payload": payload}
            built_at = time.time()
            with _LOCK:
                cache = _CACHES.setdefault(key, {})
                cache["payload"] = dict(payload)
                cache["built_at"] = built_at
                cache["building"] = False
                cache["error"] = None
            return _with_cache_meta(payload, "fresh", built_at, ttl_seconds, None)
        except Exception as exc:  # pragma: no cover - defensive runtime guard.
            with _LOCK:
                cache = _CACHES.setdefault(key, {})
                cache["building"] = False
                cache["error"] = f"{type(exc).__name__}: {exc}"

    if not building:
        start_cache_refresh(key, builder, serialize_refresh=serialize_refresh)

    if isinstance(payload, dict):
        return _with_cache_meta(payload, "refreshing", built_at, ttl_seconds, None)

    with _LOCK:
        error = _CACHES.get(key, {}).get("error")
    return _with_cache_meta(fallback(), "warming", None, ttl_seconds, error)


def start_cache_refresh(
    key: str,
    builder: Builder,
    *,
    delay_seconds: float = 0.2,
    serialize_refresh: bool = True,
) -> bool:
    """Start a background refresh for a cache-first packet.

    This lets API startup prewarm hot read-only status cards before the browser
    asks for them. The builder still runs through the shared serial refresh
    guard, so prewarm work cannot stampede expensive evidence reads.
    """

    with _LOCK:
        cache = _CACHES.setdefault(
            key,
            {"payload": None, "built_at": 0.0, "building": False, "error": None, "refresh_started_at": 0.0},
        )
        if cache.get("building"):
            return False
        cache["building"] = True
        cache["refresh_started_at"] = time.time()

    thread = threading.Timer(delay_seconds, _refresh, args=(key, builder, serialize_refresh))
    thread.name = f"cas-forex-route-cache-{key}"
    thread.daemon = True
    thread.start()
    return True


def _refresh(key: str, builder: Builder, serialize_refresh: bool = True) -> None:
    try:
        payload = run_serial_refresh(builder) if serialize_refresh else builder()
        if not isinstance(payload, dict):
            payload = {"status": "UNAVAILABLE", "payload": payload}
        with _LOCK:
            cache = _CACHES.setdefault(key, {})
            cache["payload"] = dict(payload)
            cache["built_at"] = time.time()
            cache["error"] = None
            cache["refresh_started_at"] = 0.0
    except Exception as exc:  # pragma: no cover - defensive runtime guard.
        with _LOCK:
            cache = _CACHES.setdefault(key, {})
            cache["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        with _LOCK:
            cache = _CACHES.setdefault(key, {})
            cache["building"] = False
            cache["refresh_started_at"] = 0.0


def run_serial_refresh(builder: Builder) -> dict[str, Any]:
    with _REFRESH_SEMAPHORE:
        return builder()


def _with_cache_meta(
    payload: dict[str, Any],
    status: str,
    built_at: float | None,
    ttl_seconds: float,
    error: Any,
) -> dict[str, Any]:
    now = time.time()
    age_seconds = None if built_at is None else max(0.0, now - built_at)
    out = dict(payload)
    out["cache_status"] = status
    out["cache_built_at_epoch"] = built_at
    out["cache_generated_at_iso"] = datetime.fromtimestamp(built_at, timezone.utc).isoformat() if built_at else None
    out["cache_age_seconds"] = age_seconds
    out["cache_ttl_seconds"] = ttl_seconds
    out["cache_stale"] = bool(age_seconds is not None and age_seconds > ttl_seconds)
    out["cache_refreshing"] = status == "refreshing"
    if error:
        out["cache_error"] = error
    return out
