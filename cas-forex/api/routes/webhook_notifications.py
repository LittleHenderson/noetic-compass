"""HTTP routes for operator webhook-notification subscriptions.

Web Push needs the operator's phone to be online with a registered
service worker; webhooks (Slack / Discord / Teams / custom) work as
long as the operator already has a chat channel that accepts incoming
webhooks. This route is the subscribe / unsubscribe / list / test
chassis; the dispatcher loop wiring is a follow-on slice.

Framing (observational, never advisory):
    Notifications surface what the SYSTEM DID. They MUST NOT include
    trade-pick language. The dispatcher refuses to POST any payload
    whose title or body matches an observational guard phrase — that
    refusal is also enforced here at the test endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..route_cache import cache_first_payload
from cas_forex.webhook_notifications import (
    WebhookDispatchResult,
    WebhookSubscription,
    WebhookSubscriptionStore,
    WebhookTransport,
    build_webhook_subscription,
    dispatch_webhook,
    mask_webhook_url,
    webhook_subscription_id,
)
from cas_forex.critical_notifications import (
    build_critical_alert_test_event,
    build_critical_notification_delivery_readiness,
    build_critical_notification_report,
    emit_critical_notification,
)


router = APIRouter()


# ---------------------------------------------------------------------------
# Module-level singleton store + test-injection hooks
# ---------------------------------------------------------------------------


_STORE: WebhookSubscriptionStore = WebhookSubscriptionStore()
_TEST_TRANSPORT: Optional[WebhookTransport] = None


def get_store() -> WebhookSubscriptionStore:
    return _STORE


def set_store_for_testing(store: WebhookSubscriptionStore) -> None:
    """Replace the process-singleton store. Tests only."""
    global _STORE
    _STORE = store


def reset_store_for_testing() -> None:
    """Reset to a default store rooted at the default JSONL path. Tests only."""
    global _STORE
    _STORE = WebhookSubscriptionStore()


def set_transport_for_testing(transport: Optional[WebhookTransport]) -> None:
    """Inject a dispatch transport closure. Tests only. Pass None to clear."""
    global _TEST_TRANSPORT
    _TEST_TRANSPORT = transport


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class SubscribeRequest(BaseModel):
    webhook_url: Optional[str] = None
    label: str = ""


class UnsubscribeRequest(BaseModel):
    webhook_url: Optional[str] = None
    subscription_id: Optional[str] = None


class TestWebhookRequest(BaseModel):
    label: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


class CriticalTestRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_subscription(sub: WebhookSubscription) -> Dict[str, Any]:
    return {
        "subscription_id": sub.subscription_id,
        "webhook_url_masked": sub.webhook_url_masked,
        "label": sub.label,
        "created_at_iso": sub.created_at_iso,
        "last_used_at_iso": sub.last_used_at_iso,
    }


def _serialize_dispatch(result: WebhookDispatchResult) -> Dict[str, Any]:
    return {
        "subscription_id": webhook_subscription_id(result.webhook_url) if result.webhook_url else "",
        "webhook_url_masked": mask_webhook_url(result.webhook_url),
        "success": result.success,
        "status_code": result.status_code,
        "error_message": result.error_message,
        "response_snippet": result.response_snippet,
    }


def _subscriptions_payload() -> Dict[str, Any]:
    subs = get_store().list_all()
    return {
        "subscriptions": [_serialize_subscription(s) for s in subs],
        "total_subscriptions": len(subs),
    }


def _subscriptions_warming() -> Dict[str, Any]:
    return {
        "subscriptions": [],
        "total_subscriptions": 0,
        "detail": "Webhook subscription cache is warming.",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/subscribe")
async def subscribe(body: SubscribeRequest) -> Dict[str, Any]:
    """Persist a webhook subscription. Replaces any prior record with
    the same URL (URL is the dedupe key)."""
    if not body.webhook_url:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_field", "message": "webhook_url is required"},
        )

    sub = build_webhook_subscription(
        webhook_url=body.webhook_url,
        label=body.label or "",
    )
    store = get_store()
    store.add(sub)
    return {
        "subscription": _serialize_subscription(sub),
        "total_subscriptions": len(store.list_all()),
    }


@router.post("/unsubscribe")
async def unsubscribe(body: UnsubscribeRequest) -> Response:
    """Drop the subscription with the given id or URL. Idempotent — always
    returns 204 regardless of whether the subscription existed."""
    identifier = body.subscription_id or body.webhook_url
    if identifier:
        get_store().remove(identifier)
    return Response(status_code=204)


@router.get("/subscriptions")
async def list_subscriptions() -> Dict[str, Any]:
    # Operator-only in the assembled app: api.server's owner-auth middleware
    # admits loopback or a paired LAN phone before this route is reached.
    return cache_first_payload(
        "webhook_notification_subscriptions",
        builder=_subscriptions_payload,
        fallback=_subscriptions_warming,
        ttl_seconds=10.0,
    )


@router.get("/critical-audit")
async def critical_audit(limit: int = 25) -> Dict[str, Any]:
    """Recent critical notification events and delivery attempts."""
    return build_critical_notification_report(limit)


@router.get("/critical-readiness")
async def critical_readiness(limit: int = 25) -> Dict[str, Any]:
    """Read-only delivery readiness for critical notification destinations."""
    return build_critical_notification_delivery_readiness(limit, store=get_store())


@router.post("/test")
async def test_webhook(body: TestWebhookRequest) -> Dict[str, Any]:
    """Dispatch an observational test payload to every (or label-filtered)
    webhook. Returns one WebhookDispatchResult per attempted URL.

    Without a transport injected and without ``requests`` reachable,
    each result is ``success=False`` with a documented error message.
    """
    subs = get_store().list_all()
    if body.label is not None:
        subs = [s for s in subs if s.label == body.label]

    title = body.title or "CAS Forex"
    text = body.body or "Test notification from the cockpit (observational)."
    payload: Dict[str, Any] = {"title": title, "body": text}

    results: List[WebhookDispatchResult] = []
    for sub in subs:
        result = dispatch_webhook(
            subscription=sub,
            payload=payload,
            transport=_TEST_TRANSPORT,
        )
        results.append(result)

    return {"results": [_serialize_dispatch(r) for r in results]}


@router.post("/critical-test")
async def test_critical_notification(body: CriticalTestRequest) -> Dict[str, Any]:
    """Emit one observational critical-alert test through the real critical-notification
    audit/delivery path so readiness can prove off-screen delivery, not only config."""
    audit = emit_critical_notification(
        build_critical_alert_test_event(
            title=body.title or "Critical alert test",
            body=body.body or "Operator-triggered critical alert test from Settings (observational).",
        ),
        source="api.webhook_notifications.critical_test",
        store=get_store(),
        transport=_TEST_TRANSPORT,
    )
    readiness = build_critical_notification_delivery_readiness(store=get_store())
    return {
        "report_kind": "cas_forex_critical_notification_test",
        "status": "DISPATCHED" if int(audit.get("dispatch_attempt_count") or 0) > 0 else "NO_DESTINATIONS",
        "audit": audit,
        "readiness": readiness,
        "claim_boundary": (
            "Critical alert test emits one observational test event through the "
            "existing audit/delivery path. It does not place orders, change "
            "risk settings, move money, or authorize live trading."
        ),
    }
