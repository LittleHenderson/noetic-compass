"""Web Push subscription store and dispatcher primitive.

This module is the chassis for operator-facing push notifications: a
file-backed JSONL store of Web Push subscriptions plus a dispatcher
that can either use an injected transport closure or resolve a
server-side ``pywebpush`` transport from the local VAPID config.

Framing note (observational, never advisory):
    Notifications surface what the SYSTEM DID — a trade executed, a loop
    stalled, a runtime gate flipped. They MUST NEVER include trade-pick
    language ("you should buy", "good entry", etc.). CAS is the operator's
    instrument panel, not a trade advisor.

Dispatch backend behavior:
    Real Web Push delivery requires a VAPID-signed POST to the
    endpoint URL using the subscription's p256dh + auth keys. When no
    transport closure is injected, ``dispatch_test_push`` tries to
    resolve a default ``pywebpush`` transport from the local runtime.
    If ``pywebpush`` is unavailable or the required VAPID private key /
    subject are missing, it returns a documented ``success=False``
    result explaining the gap.

Storage:
    Subscriptions are persisted as JSONL at
    ``evidence_runs/push_subscriptions/subscriptions.jsonl`` with the
    endpoint and Web Push auth material encrypted at rest. Legacy
    plaintext rows are still readable so they can be migrated on the
    next read/write. Writes are atomic (temp file + ``os.replace``). The
    store assumes a single writer process; if the API moves to
    multi-worker uvicorn this needs a file lock or a Redis/SQLite backend.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlsplit

from cas_forex.secret_envelope import (
    is_secret_envelope,
    protect_secret,
    unprotect_secret,
)
from cas_forex.push_delivery_control import resolve_push_delivery_config


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PushSubscription:
    """Web Push subscription record.

    Mirrors the browser-side ``PushSubscription.toJSON()`` shape:
    an endpoint URL plus the ``p256dh`` and ``auth`` keys used for
    VAPID-signed payload encryption.
    """

    endpoint: str
    keys_p256dh: str
    keys_auth: str
    created_at_iso: str
    label: str = ""

    @property
    def subscription_id(self) -> str:
        return push_subscription_id(self.endpoint)

    @property
    def endpoint_masked(self) -> str:
        return mask_push_endpoint(self.endpoint)

    def to_jsonl_dict(self) -> dict:
        return {
            "endpoint": protect_secret(self.endpoint),
            "keys_p256dh": protect_secret(self.keys_p256dh),
            "keys_auth": protect_secret(self.keys_auth),
            "created_at_iso": self.created_at_iso,
            "label": self.label,
        }

    @classmethod
    def from_jsonl_dict(cls, payload: dict) -> "PushSubscription":
        endpoint = unprotect_secret(payload.get("endpoint")).strip()
        keys_p256dh = unprotect_secret(payload.get("keys_p256dh")).strip()
        keys_auth = unprotect_secret(payload.get("keys_auth")).strip()
        if not endpoint or not keys_p256dh or not keys_auth:
            raise KeyError("push_subscription_secret")
        return cls(
            endpoint=endpoint,
            keys_p256dh=keys_p256dh,
            keys_auth=keys_auth,
            created_at_iso=str(payload.get("created_at_iso", "")),
            label=str(payload.get("label", "") or ""),
        )


@dataclass(frozen=True)
class PushDispatchResult:
    """Outcome of one push delivery attempt — one record per endpoint."""

    endpoint: str
    success: bool
    status_code: Optional[int]
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Defaults / paths
# ---------------------------------------------------------------------------


DEFAULT_STORE_DIR = Path("evidence_runs") / "push_subscriptions"
DEFAULT_STORE_FILENAME = "subscriptions.jsonl"

# Documented dispatch-backend gap. Surfaced both in error_message and in
# logs so the operator and tests can tell "we didn't send because the
# library isn't installed" apart from "we tried and the push service
# rejected the payload".
DISPATCH_BACKEND_MISSING_MESSAGE = "dispatch backend not installed (pywebpush)"
DISPATCH_CONFIG_MISSING_MESSAGE = "dispatch backend not configured (missing VAPID private key or subject)"


def _utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def push_subscription_id(endpoint: str) -> str:
    normalized = str(endpoint or "").strip().encode("utf-8")
    return f"pushsub_{sha256(normalized).hexdigest()[:24]}"


def mask_push_endpoint(endpoint: str) -> str:
    value = str(endpoint or "").strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/..."
    return "configured-push-endpoint-redacted"


# ---------------------------------------------------------------------------
# File-backed JSONL store
# ---------------------------------------------------------------------------


class PushSubscriptionStore:
    """File-backed JSONL store of :class:`PushSubscription` records.

    Atomic write semantics: every mutation re-serializes the full list
    via temp file + ``os.replace`` so a crash mid-write can only leave
    the previous good file in place. Single-writer assumption — see the
    module docstring for the concurrency caveat.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = Path(path) if path is not None else (DEFAULT_STORE_DIR / DEFAULT_STORE_FILENAME)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # -- introspection ------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    # -- read ---------------------------------------------------------------

    def list_all(self) -> list[PushSubscription]:
        """Return every subscription currently on disk, in insertion order."""
        if not self._path.exists():
            return []
        subs: list[PushSubscription] = []
        migrated_plaintext = False
        with self._path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    # Skip corrupt lines rather than refuse to read; the
                    # next atomic write will rewrite cleanly.
                    continue
                try:
                    subs.append(PushSubscription.from_jsonl_dict(payload))
                except (KeyError, TypeError, ValueError):
                    continue
                if not (
                    is_secret_envelope(payload.get("endpoint"))
                    and is_secret_envelope(payload.get("keys_p256dh"))
                    and is_secret_envelope(payload.get("keys_auth"))
                ):
                    migrated_plaintext = True
        if migrated_plaintext and subs:
            try:
                self._atomic_write(subs)
            except OSError:
                pass
        return subs

    # -- mutate -------------------------------------------------------------

    def add(self, sub: PushSubscription) -> PushSubscription:
        """Persist ``sub``. If an existing record shares the endpoint,
        the new record replaces it (endpoint uniqueness is the dedupe key)."""
        current = self.list_all()
        deduped = [s for s in current if s.endpoint != sub.endpoint]
        deduped.append(sub)
        self._atomic_write(deduped)
        return sub

    def remove(self, identifier: str) -> bool:
        """Drop the subscription identified by endpoint or subscription id.

        Returns True if a record was removed, False if no such subscription was
        present.
        """
        current = self.list_all()
        remaining = [s for s in current if not _matches_subscription_identifier(s, identifier)]
        if len(remaining) == len(current):
            return False
        self._atomic_write(remaining)
        return True

    def clear(self) -> None:
        """Remove every subscription (used by tests and the operator
        "forget my devices" affordance)."""
        self._atomic_write([])

    # -- internals ----------------------------------------------------------

    def _atomic_write(self, subs: list[PushSubscription]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=self._path.name + ".",
            suffix=".tmp",
            dir=str(self._path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                for sub in subs:
                    fh.write(json.dumps(sub.to_jsonl_dict(), ensure_ascii=False))
                    fh.write("\n")
            os.replace(tmp_path, self._path)
        except Exception:
            # Best-effort cleanup of the temp file on failure; re-raise.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------


def build_subscription(
    *,
    endpoint: str,
    keys_p256dh: str,
    keys_auth: str,
    label: str = "",
    created_at_iso: Optional[str] = None,
) -> PushSubscription:
    """Construct a :class:`PushSubscription` with a default UTC timestamp."""
    return PushSubscription(
        endpoint=endpoint,
        keys_p256dh=keys_p256dh,
        keys_auth=keys_auth,
        created_at_iso=created_at_iso or _utcnow_iso(),
        label=label,
    )


def _matches_subscription_identifier(sub: PushSubscription, identifier: str) -> bool:
    normalized = str(identifier or "").strip()
    if not normalized:
        return False
    return normalized == sub.endpoint or normalized == sub.subscription_id


# ---------------------------------------------------------------------------
# Dispatcher primitive
# ---------------------------------------------------------------------------


# A dispatch transport receives the subscription + JSON payload and returns
# a `PushDispatchResult`. Tests inject a stub. Production wiring will inject
# a closure that calls ``pywebpush.webpush(...)``.
PushTransport = Callable[[PushSubscription, dict], PushDispatchResult]


def _resolve_default_transport() -> tuple[Optional[PushTransport], Optional[str]]:
    try:
        from pywebpush import WebPushException, webpush  # type: ignore[import-not-found]
    except Exception:
        return None, DISPATCH_BACKEND_MISSING_MESSAGE

    config = resolve_push_delivery_config()
    private_key = str(config["vapid_private_key"]["value"] or "").strip()
    subject = str(config["vapid_subject"]["value"] or "").strip()
    if not private_key or not subject:
        return None, DISPATCH_CONFIG_MISSING_MESSAGE

    def transport(subscription: PushSubscription, payload: dict) -> PushDispatchResult:
        try:
            response = webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.keys_p256dh,
                        "auth": subscription.keys_auth,
                    },
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
                timeout=10,
            )
            status_code = int(getattr(response, "status_code", 201) or 201)
            return PushDispatchResult(
                endpoint=subscription.endpoint,
                success=200 <= status_code < 300,
                status_code=status_code,
                error_message=None if 200 <= status_code < 300 else f"push service returned HTTP {status_code}",
            )
        except WebPushException as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            error_message = str(exc) or repr(exc)
            return PushDispatchResult(
                endpoint=subscription.endpoint,
                success=False,
                status_code=int(status_code) if status_code is not None else None,
                error_message=error_message,
            )

    return transport, None


def _ensure_observational_payload(payload: dict) -> None:
    """Light defense against trade-advisory language in the payload body.

    This is a guardrail, not a security boundary — it raises ValueError
    if obvious advisory phrases sneak in. The architectural commitment
    is that the *call sites* never construct advisory messages; this
    check is here so a regression in a call site fails loudly in tests.
    """
    advisory_phrases = (
        "you should buy",
        "you should sell",
        "good entry",
        "recommended trade",
        "we recommend",
    )
    text_fields = []
    for key in ("title", "body", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            text_fields.append(value.lower())
    joined = " ".join(text_fields)
    for phrase in advisory_phrases:
        if phrase in joined:
            raise ValueError(
                "push payload contains advisory phrase "
                f"({phrase!r}); notifications must be observational only"
            )


def dispatch_test_push(
    *,
    subscription: PushSubscription,
    payload: dict,
    transport: Optional[PushTransport] = None,
) -> PushDispatchResult:
    """Dispatch one observational push to ``subscription``.

    When ``transport`` is injected (the test pattern, or the future
    pywebpush-backed wiring), it's called with the subscription + payload
    and its return value is propagated as the result.

    When ``transport`` is None, this function tries to resolve the
    default server-side backend. If the runtime lacks ``pywebpush`` or
    the required VAPID config, it returns a documented
    ``success=False`` result.
    """
    _ensure_observational_payload(payload)

    if transport is None:
        transport, error_message = _resolve_default_transport()
        if transport is None:
            return PushDispatchResult(
                endpoint=subscription.endpoint,
                success=False,
                status_code=None,
                error_message=error_message or DISPATCH_BACKEND_MISSING_MESSAGE,
            )

    try:
        return transport(subscription, payload)
    except Exception as exc:  # pragma: no cover - thin pass-through
        return PushDispatchResult(
            endpoint=subscription.endpoint,
            success=False,
            status_code=None,
            error_message=f"transport raised: {exc!r}",
        )


__all__ = [
    "DISPATCH_BACKEND_MISSING_MESSAGE",
    "DISPATCH_CONFIG_MISSING_MESSAGE",
    "DEFAULT_STORE_DIR",
    "DEFAULT_STORE_FILENAME",
    "PushDispatchResult",
    "PushSubscription",
    "PushSubscriptionStore",
    "PushTransport",
    "build_subscription",
    "dispatch_test_push",
    "mask_push_endpoint",
    "push_subscription_id",
]
