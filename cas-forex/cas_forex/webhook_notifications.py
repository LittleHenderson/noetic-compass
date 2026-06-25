"""Webhook subscription store and dispatcher primitive.

Webhooks are the robust fallback notification channel: the operator
pastes a Slack / Discord / Teams / custom incoming-webhook URL once,
and observational notification events POST to it as JSON. The operator's
phone does not need to be online with a service worker registered, so
this channel is more durable than Web Push.

Framing note (observational, never advisory):
    Webhook payloads surface what the SYSTEM DID — a trade executed,
    a loop stalled, a runtime gate flipped. They MUST NEVER include
    trade-pick language ("you should buy", "good entry", etc.). CAS
    is the operator's instrument panel, not a trade advisor. The
    dispatcher validates payload text against ``OBSERVATIONAL_GUARD_PHRASES``
    BEFORE attempting any HTTP call. If any forbidden phrase appears
    in the rendered payload's ``title`` or ``body`` fields the dispatch
    is refused with ``success=False`` and a clear error message.

Storage:
    Subscriptions are persisted as JSONL at
    ``evidence_runs/webhook_subscriptions/subscriptions.jsonl``. Writes
    are atomic (temp file + ``os.replace``). The store assumes a single
    writer process; if the API moves to multi-worker uvicorn this needs
    a file lock or a Redis/SQLite backend.

Transport:
    ``dispatch_webhook`` accepts an injectable transport callable so
    tests never make real HTTP calls. When no transport is injected the
    function attempts ``requests.post`` (``requests`` is already a
    project dependency). If neither path is available a clean failure
    result is returned documenting the gap.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WebhookSubscription:
    """Operator-registered webhook target.

    ``webhook_url`` is the destination POST URL (Slack incoming hook,
    Discord webhook, Teams workflow URL, custom server endpoint). ``label``
    is a free-form operator-supplied tag (e.g. "slack-trades", "discord-alerts").
    """

    webhook_url: str
    label: str
    created_at_iso: str
    last_used_at_iso: Optional[str]

    def to_jsonl_dict(self) -> dict:
        return {
            "webhook_url": self.webhook_url,
            "label": self.label,
            "created_at_iso": self.created_at_iso,
            "last_used_at_iso": self.last_used_at_iso,
        }

    @classmethod
    def from_jsonl_dict(cls, payload: dict) -> "WebhookSubscription":
        last_used = payload.get("last_used_at_iso")
        return cls(
            webhook_url=str(payload["webhook_url"]),
            label=str(payload.get("label", "") or ""),
            created_at_iso=str(payload.get("created_at_iso", "")),
            last_used_at_iso=str(last_used) if last_used else None,
        )


@dataclass(frozen=True)
class WebhookDispatchResult:
    """Outcome of one webhook delivery attempt — one record per URL.

    ``response_snippet`` is the first 200 characters of the response
    body when a transport returned one; useful for surfacing Slack /
    Discord "invalid_payload" style debug messages to the operator
    without leaking the full body into the audit log.
    """

    webhook_url: str
    success: bool
    status_code: Optional[int]
    error_message: Optional[str]
    response_snippet: Optional[str]


# ---------------------------------------------------------------------------
# Defaults / paths
# ---------------------------------------------------------------------------


DEFAULT_STORE_DIR = Path("evidence_runs") / "webhook_subscriptions"
DEFAULT_STORE_FILENAME = "subscriptions.jsonl"

# Documented gap when neither a transport closure nor ``requests`` is
# available. ``requests`` IS in this repo's requirements today; this
# message exists to make the failure mode obvious if a future
# environment strips it out.
DISPATCH_BACKEND_MISSING_MESSAGE = "dispatch backend not installed (requests)"
ADVISORY_PHRASE_ERROR_MESSAGE = "advisory phrase in payload"

# Phrases that betray trade-advisory framing. The dispatcher refuses to
# POST any payload whose ``title`` or ``body`` contains one of these
# (case-insensitive substring match). This is a regression guard, NOT a
# security boundary — the architectural commitment is that the call
# sites never construct advisory messages in the first place.
OBSERVATIONAL_GUARD_PHRASES: tuple[str, ...] = (
    "you should buy",
    "you should sell",
    "good entry",
    "good exit",
    "recommended trade",
    "we recommend",
    "buy now",
    "sell now",
    "take profit now",
    "best trade",
    "hot tip",
)


def _utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# File-backed JSONL store
# ---------------------------------------------------------------------------


class WebhookSubscriptionStore:
    """File-backed JSONL store of :class:`WebhookSubscription` records.

    Atomic write semantics: every mutation re-serializes the full list
    via temp file + ``os.replace`` so a crash mid-write can only leave
    the previous good file in place. Single-writer assumption — see the
    module docstring for the concurrency caveat. URL is the dedupe key.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = (
            Path(path)
            if path is not None
            else (DEFAULT_STORE_DIR / DEFAULT_STORE_FILENAME)
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # -- introspection ------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    # -- read ---------------------------------------------------------------

    def list_all(self) -> list[WebhookSubscription]:
        """Return every subscription currently on disk, in insertion order."""
        if not self._path.exists():
            return []
        subs: list[WebhookSubscription] = []
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
                    subs.append(WebhookSubscription.from_jsonl_dict(payload))
                except (KeyError, TypeError):
                    continue
        return subs

    # -- mutate -------------------------------------------------------------

    def add(self, sub: WebhookSubscription) -> WebhookSubscription:
        """Persist ``sub``. If an existing record shares the URL, the
        new record replaces it (URL uniqueness is the dedupe key)."""
        current = self.list_all()
        deduped = [s for s in current if s.webhook_url != sub.webhook_url]
        deduped.append(sub)
        self._atomic_write(deduped)
        return sub

    def remove(self, webhook_url: str) -> bool:
        """Drop the subscription identified by ``webhook_url``. Returns
        True if a record was removed, False if no such URL was present."""
        current = self.list_all()
        remaining = [s for s in current if s.webhook_url != webhook_url]
        if len(remaining) == len(current):
            return False
        self._atomic_write(remaining)
        return True

    def clear(self) -> None:
        """Remove every subscription (used by tests and the operator
        "forget my webhooks" affordance)."""
        self._atomic_write([])

    def update_last_used(self, webhook_url: str, when_iso: str) -> bool:
        """Set ``last_used_at_iso`` on the record matching ``webhook_url``.

        Returns True if a record was updated, False if no such URL was
        present. The update is persisted atomically.
        """
        current = self.list_all()
        updated = False
        next_list: list[WebhookSubscription] = []
        for s in current:
            if s.webhook_url == webhook_url:
                next_list.append(
                    WebhookSubscription(
                        webhook_url=s.webhook_url,
                        label=s.label,
                        created_at_iso=s.created_at_iso,
                        last_used_at_iso=when_iso,
                    )
                )
                updated = True
            else:
                next_list.append(s)
        if updated:
            self._atomic_write(next_list)
        return updated

    # -- internals ----------------------------------------------------------

    def _atomic_write(self, subs: list[WebhookSubscription]) -> None:
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


def build_webhook_subscription(
    *,
    webhook_url: str,
    label: str = "",
    created_at_iso: Optional[str] = None,
    last_used_at_iso: Optional[str] = None,
) -> WebhookSubscription:
    """Construct a :class:`WebhookSubscription` with a default UTC timestamp."""
    return WebhookSubscription(
        webhook_url=webhook_url,
        label=label,
        created_at_iso=created_at_iso or _utcnow_iso(),
        last_used_at_iso=last_used_at_iso,
    )


# ---------------------------------------------------------------------------
# Observational guard
# ---------------------------------------------------------------------------


def _contains_advisory_phrase(payload: Mapping[str, Any]) -> Optional[str]:
    """Return the first guard phrase found in ``payload``'s text fields,
    or None when the payload is clean. Case-insensitive substring match."""
    text_fields: list[str] = []
    for key in ("title", "body"):
        value = payload.get(key) if isinstance(payload, Mapping) else None
        if isinstance(value, str):
            text_fields.append(value.lower())
    if not text_fields:
        return None
    joined = " ".join(text_fields)
    for phrase in OBSERVATIONAL_GUARD_PHRASES:
        if phrase in joined:
            return phrase
    return None


# ---------------------------------------------------------------------------
# Dispatcher primitive
# ---------------------------------------------------------------------------


# A transport receives (url, json, headers, timeout) keyword-style and
# returns a response-like object exposing ``status_code`` and ``text``.
# Tests inject a stub; production uses ``requests.post``.
WebhookTransport = Callable[..., Any]


def _snippet(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:  # pragma: no cover - defensive
            return None
    return text[:200]


def dispatch_webhook(
    *,
    subscription: WebhookSubscription,
    payload: Mapping[str, Any],
    transport: Optional[WebhookTransport] = None,
    timeout_seconds: float = 10.0,
) -> WebhookDispatchResult:
    """POST ``payload`` as JSON to ``subscription.webhook_url``.

    Order of operations:

    1. Validate ``payload`` against ``OBSERVATIONAL_GUARD_PHRASES``. If
       any forbidden phrase appears in the ``title`` or ``body`` field
       the dispatch is REFUSED — no HTTP call is made — and the result
       carries ``success=False, error_message="advisory phrase in payload"``.
    2. If ``transport`` is injected, call it with
       ``(url=..., json=..., headers=..., timeout=...)`` and translate
       its response. ``response.status_code`` in [200, 300) is success.
    3. If no transport is injected, attempt ``requests.post``. If the
       ``requests`` import fails, return a clean failure result
       documenting the gap.

    This function never raises. Transport exceptions are caught and
    surfaced as ``success=False`` with the exception repr in
    ``error_message``.
    """
    offending = _contains_advisory_phrase(payload)
    if offending is not None:
        return WebhookDispatchResult(
            webhook_url=subscription.webhook_url,
            success=False,
            status_code=None,
            error_message=f"{ADVISORY_PHRASE_ERROR_MESSAGE}: {offending!r}",
            response_snippet=None,
        )

    payload_dict = dict(payload)
    headers = {"Content-Type": "application/json"}

    # Resolve transport: injected closure wins; fall back to requests.post.
    resolved_transport: Optional[WebhookTransport] = transport
    if resolved_transport is None:
        try:
            import requests  # type: ignore

            resolved_transport = requests.post  # type: ignore[assignment]
        except Exception:  # pragma: no cover - requests is in requirements
            return WebhookDispatchResult(
                webhook_url=subscription.webhook_url,
                success=False,
                status_code=None,
                error_message=DISPATCH_BACKEND_MISSING_MESSAGE,
                response_snippet=None,
            )

    try:
        response = resolved_transport(
            subscription.webhook_url,
            json=payload_dict,
            headers=headers,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return WebhookDispatchResult(
            webhook_url=subscription.webhook_url,
            success=False,
            status_code=None,
            error_message=f"transport raised: {exc!r}",
            response_snippet=None,
        )

    status_code = getattr(response, "status_code", None)
    raw_text = getattr(response, "text", None)
    snippet = _snippet(raw_text)

    try:
        status_int = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        status_int = None

    if status_int is not None and 200 <= status_int < 300:
        return WebhookDispatchResult(
            webhook_url=subscription.webhook_url,
            success=True,
            status_code=status_int,
            error_message=None,
            response_snippet=snippet,
        )

    return WebhookDispatchResult(
        webhook_url=subscription.webhook_url,
        success=False,
        status_code=status_int,
        error_message=f"non-success status: {status_int!r}",
        response_snippet=snippet,
    )


__all__ = [
    "ADVISORY_PHRASE_ERROR_MESSAGE",
    "DEFAULT_STORE_DIR",
    "DEFAULT_STORE_FILENAME",
    "DISPATCH_BACKEND_MISSING_MESSAGE",
    "OBSERVATIONAL_GUARD_PHRASES",
    "WebhookDispatchResult",
    "WebhookSubscription",
    "WebhookSubscriptionStore",
    "WebhookTransport",
    "build_webhook_subscription",
    "dispatch_webhook",
]
