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

from ..route_cache import cache_first_payload, invalidate_cache
from cas_forex.push_delivery_control import (
    CLAIM_BOUNDARY as PUSH_DELIVERY_CLAIM_BOUNDARY,
    DEFAULT_OVERRIDE_PATH as PUSH_DELIVERY_DEFAULT_OVERRIDE_PATH,
    PRIVATE_KEY_ENV_KEYS,
    SUBJECT_ENV_KEYS,
    build_push_delivery_backend_report,
    clear_push_delivery_overrides,
    set_push_delivery_overrides,
)
from cas_forex.push_notifications import (
    PushDispatchResult,
    PushSubscription,
    PushSubscriptionStore,
    PushTransport,
    build_subscription,
    dispatch_test_push,
    mask_push_endpoint,
    push_subscription_id,
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
    subscription_id: Optional[str] = None


class TestPushRequest(BaseModel):
    label: Optional[str] = None
    payload: Optional[Dict[str, Any]] = Field(default=None)


class PushDeliveryBackendUpdate(BaseModel):
    vapid_public_key: Optional[str] = None
    vapid_private_key: Optional[str] = None
    vapid_subject: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_subscription(sub: PushSubscription) -> Dict[str, Any]:
    return {
        "subscription_id": sub.subscription_id,
        "endpoint_masked": sub.endpoint_masked,
        "label": sub.label,
        "created_at_iso": sub.created_at_iso,
    }


def _serialize_dispatch(result: PushDispatchResult) -> Dict[str, Any]:
    return {
        "subscription_id": push_subscription_id(result.endpoint) if result.endpoint else "",
        "endpoint_masked": mask_push_endpoint(result.endpoint),
        "success": result.success,
        "status_code": result.status_code,
        "error_message": result.error_message,
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
        "detail": "Push subscription cache is warming.",
    }


def _backend_payload() -> Dict[str, Any]:
    return build_push_delivery_backend_report(
        subscription_count=len(get_store().list_all()),
    )


def _backend_warming() -> Dict[str, Any]:
    return {
        "report_kind": "cas_forex_push_delivery_backend",
        "status": "WARMING",
        "dispatch_backend_available": False,
        "dispatch_backend_package": "pywebpush",
        "dispatch_backend_version": None,
        "subscription_count": 0,
        "browser_subscriptions_present": False,
        "subscription_registration_ready": False,
        "dispatch_ready": False,
        "fully_ready": False,
        "blockers": ["Push delivery backend status is warming."],
        "next_action": "Wait for the push backend status packet to warm, then retry.",
        "vapid_public_key": "",
        "vapid_public_key_configured": False,
        "vapid_public_key_configured_key": None,
        "vapid_public_key_source": "unknown",
        "vapid_public_key_masked": None,
        "vapid_private_key": {
            "configured": False,
            "configured_key": None,
            "masked_value": None,
            "source": "unknown",
            "env_keys": list(PRIVATE_KEY_ENV_KEYS),
        },
        "vapid_subject": {
            "configured": False,
            "value": "",
            "configured_key": None,
            "masked_value": None,
            "source": "unknown",
            "env_keys": list(SUBJECT_ENV_KEYS),
        },
        "runtime_override_path": str(PUSH_DELIVERY_DEFAULT_OVERRIDE_PATH),
        "secret_storage": {"at_rest_encrypted": True},
        "claim_boundary": PUSH_DELIVERY_CLAIM_BOUNDARY,
    }


def _invalidate_notification_caches(*, include_security_posture: bool = False) -> None:
    keys = ["push_notification_subscriptions", "push_notification_backend"]
    if include_security_posture:
        keys.append("settings_security_posture")
    invalidate_cache(*keys)


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
    _invalidate_notification_caches()
    return {
        "subscription": _serialize_subscription(sub),
        "total_subscriptions": len(store.list_all()),
    }


@router.post("/unsubscribe")
async def unsubscribe(body: UnsubscribeRequest) -> Response:
    """Drop the subscription with the given endpoint. Idempotent — always
    returns 204 regardless of whether the endpoint existed."""
    identifier = body.subscription_id or body.endpoint
    if identifier:
        get_store().remove(identifier)
        _invalidate_notification_caches()
    return Response(status_code=204)


@router.get("/subscriptions")
async def list_subscriptions() -> Dict[str, Any]:
    # Operator-only in the assembled app: api.server's owner-auth middleware
    # admits loopback or a paired LAN phone before this route is reached.
    return cache_first_payload(
        "push_notification_subscriptions",
        builder=_subscriptions_payload,
        fallback=_subscriptions_warming,
        ttl_seconds=10.0,
    )


@router.get("/backend")
async def get_push_backend() -> Dict[str, Any]:
    return cache_first_payload(
        "push_notification_backend",
        builder=_backend_payload,
        fallback=_backend_warming,
        ttl_seconds=10.0,
    )


@router.post("/backend/update")
async def update_push_backend(body: PushDeliveryBackendUpdate) -> Dict[str, Any]:
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    applied_keys = set_push_delivery_overrides(**provided) if provided else []
    if applied_keys:
        _invalidate_notification_caches(include_security_posture=True)
    return {
        "report_kind": "cas_forex_push_delivery_backend_update",
        "status": "UPDATED" if applied_keys else "NO_CHANGES",
        "applied_keys": applied_keys,
        "push_backend": _backend_payload(),
        "claim_boundary": (
            "Push backend update changes only local VAPID runtime overrides for "
            "observational browser notifications. It does not place orders, move "
            "money, or authorize live trading."
        ),
    }


@router.post("/backend/reset")
async def reset_push_backend() -> Dict[str, Any]:
    cleared_keys = clear_push_delivery_overrides()
    if cleared_keys:
        _invalidate_notification_caches(include_security_posture=True)
    return {
        "report_kind": "cas_forex_push_delivery_backend_reset",
        "status": "RESET",
        "applied_keys": cleared_keys,
        "push_backend": _backend_payload(),
        "claim_boundary": (
            "Push backend reset clears only local VAPID runtime overrides. It "
            "does not remove static env configuration, place orders, move money, "
            "or authorize live trading."
        ),
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
