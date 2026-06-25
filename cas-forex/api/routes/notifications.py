"""HTTP routes for operator push-notification subscriptions.

The agent cycle trades autonomously to remove the operator from the
emotional decision loop, but the operator still wants to be notified
when meaningful things happen — a trade executes, the loop stalls, a
runtime gate flips. This route is the subscription / unsubscribe /
dispatcher chassis; wiring it into the actual agent cycle and
supervisor is a follow-on slice.

Framing (observational, never advisory):
    Notifications surface what the SYSTEM DID. They MUST NOT include
    trade-pick language ("you should buy", etc.). The dispatcher
    enforces this on the payload as a regression guard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from cas_forex.push_notifications import (
    PushDispatchResult,
    PushSubscription,
    PushSubscriptionStore,
    PushTransport,
    build_subscription,
    dispatch_test_push,
)


router = APIRouter()


# ---------------------------------------------------------------------------
# Module-level singleton store + test-injection hooks
# ---------------------------------------------------------------------------


_STORE: PushSubscriptionStore = PushSubscriptionStore()


def get_store() -> PushSubscriptionStore:
    return _STORE


def set_store_for_testing(store: PushSubscriptionStore) -> None:
    """Replace the process-singleton store. Tests only."""
    global _STORE
    _STORE = store


def reset_store_for_testing() -> None:
    """Reset to a default store rooted at the default JSONL path. Tests only."""
    global _STORE
    _STORE = PushSubscriptionStore()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class _SubscribeKeys(BaseModel):
    p256dh: Optional[str] = None
    auth: Optional[str] = None


class SubscribeRequest(BaseModel):
    endpoint: Optional[str] = None
    keys: Optional[_SubscribeKeys] = None
    label: str = ""


class UnsubscribeRequest(BaseModel):
    endpoint: Optional[str] = None


class TestPushRequest(BaseModel):
    label: Optional[str] = None
    payload: Optional[Dict[str, Any]] = Field(default=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_subscription(sub: PushSubscription) -> Dict[str, Any]:
    return {
        "endpoint": sub.endpoint,
        "keys": {"p256dh": sub.keys_p256dh, "auth": sub.keys_auth},
        "label": sub.label,
        "created_at_iso": sub.created_at_iso,
    }


def _serialize_dispatch(result: PushDispatchResult) -> Dict[str, Any]:
    return {
        "endpoint": result.endpoint,
        "success": result.success,
        "status_code": result.status_code,
        "error_message": result.error_message,
    }


# Transport hook for tests: when set, dispatch_test_push will use it.
_TEST_TRANSPORT: Optional[PushTransport] = None


def set_transport_for_testing(transport: Optional[PushTransport]) -> None:
    """Inject a dispatch transport closure. Tests only. Pass None to clear."""
    global _TEST_TRANSPORT
    _TEST_TRANSPORT = transport


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/subscribe")
async def subscribe(body: SubscribeRequest) -> Dict[str, Any]:
    """Persist a Web Push subscription. Replaces any prior record with
    the same endpoint (endpoint is the dedupe key)."""
    if not body.endpoint:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_field", "message": "endpoint is required"},
        )
    if body.keys is None or not body.keys.p256dh or not body.keys.auth:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_field",
                "message": "keys.p256dh and keys.auth are required",
            },
        )

    sub = build_subscription(
        endpoint=body.endpoint,
        keys_p256dh=body.keys.p256dh,
        keys_auth=body.keys.auth,
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
    """Drop the subscription with the given endpoint. Idempotent — always
    returns 204 regardless of whether the endpoint existed."""
    if body.endpoint:
        get_store().remove(body.endpoint)
    return Response(status_code=204)


@router.get("/subscriptions")
async def list_subscriptions() -> Dict[str, Any]:
    # TODO: operator-only — gate this behind the same auth as the cockpit
    # once the auth layer lands. Today there is no auth on /api/forex/*.
    subs = get_store().list_all()
    return {
        "subscriptions": [_serialize_subscription(s) for s in subs],
        "total_subscriptions": len(subs),
    }


@router.post("/test-push")
async def test_push(body: TestPushRequest) -> Dict[str, Any]:
    """Dispatch an observational test push to every (or label-filtered)
    subscription. Returns one PushDispatchResult per attempted endpoint.

    Without a transport injected and without ``pywebpush`` installed,
    each result is ``success=False`` with a documented error message.
    """
    subs = get_store().list_all()
    if body.label is not None:
        subs = [s for s in subs if s.label == body.label]

    payload: Dict[str, Any] = body.payload or {
        "title": "CAS Forex",
        "body": "Test notification from the cockpit (observational).",
    }

    results: List[PushDispatchResult] = []
    for sub in subs:
        result = dispatch_test_push(
            subscription=sub,
            payload=payload,
            transport=_TEST_TRANSPORT,
        )
        results.append(result)

    return {"results": [_serialize_dispatch(r) for r in results]}
