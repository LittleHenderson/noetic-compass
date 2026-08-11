"""Unit tests for the push-notification chassis.

Covers the file-backed JSONL subscription store and the pure
``dispatch_test_push`` dispatcher. The dispatcher's documented
"no backend installed" path is exercised here so the production gap
is visible in the test report.
"""

from __future__ import annotations

import json

import pytest

from cas_forex.push_notifications import (
    DISPATCH_BACKEND_MISSING_MESSAGE,
    DISPATCH_CONFIG_MISSING_MESSAGE,
    PushDispatchResult,
    PushSubscription,
    PushSubscriptionStore,
    build_subscription,
    dispatch_test_push,
)


def _store(tmp_path) -> PushSubscriptionStore:
    return PushSubscriptionStore(path=tmp_path / "subscriptions.jsonl")


def _make_sub(endpoint: str = "https://push.example/abc", label: str = "") -> PushSubscription:
    return build_subscription(
        endpoint=endpoint,
        keys_p256dh="p256dh-key",
        keys_auth="auth-key",
        label=label,
    )


# ---------------------------------------------------------------------------
# Store tests
# ---------------------------------------------------------------------------


def test_empty_store_lists_empty(tmp_path):
    store = _store(tmp_path)
    assert store.list_all() == []


def test_add_then_list_returns_record(tmp_path):
    store = _store(tmp_path)
    sub = _make_sub()
    store.add(sub)

    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0].endpoint == sub.endpoint
    assert listed[0].keys_p256dh == "p256dh-key"
    assert listed[0].keys_auth == "auth-key"
    assert listed[0].subscription_id.startswith("pushsub_")
    assert listed[0].endpoint_masked == "https://push.example/..."


def test_add_duplicate_endpoint_replaces_record(tmp_path):
    store = _store(tmp_path)
    store.add(_make_sub(label="phone-old"))
    store.add(_make_sub(label="phone-new"))

    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0].label == "phone-new"


def test_remove_returns_true_for_existing_endpoint(tmp_path):
    store = _store(tmp_path)
    sub = _make_sub()
    store.add(sub)

    assert store.remove(sub.endpoint) is True
    assert store.list_all() == []


def test_remove_accepts_subscription_id(tmp_path):
    store = _store(tmp_path)
    sub = _make_sub()
    store.add(sub)

    assert store.remove(sub.subscription_id) is True
    assert store.list_all() == []


def test_remove_returns_false_when_endpoint_absent(tmp_path):
    store = _store(tmp_path)
    assert store.remove("https://push.example/never-added") is False


def test_clear_empties_store(tmp_path):
    store = _store(tmp_path)
    store.add(_make_sub(endpoint="https://push.example/a"))
    store.add(_make_sub(endpoint="https://push.example/b"))
    assert len(store.list_all()) == 2

    store.clear()
    assert store.list_all() == []


def test_atomic_write_then_read_roundtrip_persists_to_disk(tmp_path):
    store_path = tmp_path / "subscriptions.jsonl"
    store = PushSubscriptionStore(path=store_path)
    sub = _make_sub(endpoint="https://push.example/persist", label="laptop")
    store.add(sub)

    # File exists, contains exactly one JSONL line that parses cleanly.
    assert store_path.exists()
    persisted = store_path.read_text(encoding="utf-8")
    lines = [line for line in persisted.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "https://push.example/persist" not in persisted
    assert "p256dh-key" not in persisted
    assert "auth-key" not in persisted
    assert '"encrypted": true' in persisted.lower()
    decoded = json.loads(lines[0])
    assert isinstance(decoded["endpoint"], dict)
    assert isinstance(decoded["keys_p256dh"], dict)
    assert isinstance(decoded["keys_auth"], dict)
    assert decoded["endpoint"]["encrypted"] is True
    assert decoded["keys_p256dh"]["encrypted"] is True
    assert decoded["keys_auth"]["encrypted"] is True
    assert decoded["label"] == "laptop"

    # A second store instance pointed at the same path sees the record.
    reopened = PushSubscriptionStore(path=store_path)
    listed = reopened.list_all()
    assert len(listed) == 1
    assert listed[0].endpoint == "https://push.example/persist"


def test_legacy_plaintext_push_subscription_is_migrated_to_encrypted(tmp_path):
    store_path = tmp_path / "subscriptions.jsonl"
    store_path.write_text(
        json.dumps(
            {
                "endpoint": "https://push.example/legacy",
                "keys_p256dh": "legacy-p256",
                "keys_auth": "legacy-auth",
                "created_at_iso": "2026-07-09T00:00:00+00:00",
                "label": "phone",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    store = PushSubscriptionStore(path=store_path)
    listed = store.list_all()

    assert len(listed) == 1
    assert listed[0].endpoint == "https://push.example/legacy"
    assert listed[0].keys_p256dh == "legacy-p256"
    assert listed[0].keys_auth == "legacy-auth"

    rewritten = store_path.read_text(encoding="utf-8")
    assert "https://push.example/legacy" not in rewritten
    assert "legacy-p256" not in rewritten
    assert "legacy-auth" not in rewritten
    assert '"encrypted": true' in rewritten.lower()


def test_label_preserved_through_roundtrip(tmp_path):
    store = _store(tmp_path)
    store.add(_make_sub(endpoint="https://push.example/a", label="iphone"))
    store.add(_make_sub(endpoint="https://push.example/b", label="laptop"))

    listed = {s.endpoint: s.label for s in store.list_all()}
    assert listed == {
        "https://push.example/a": "iphone",
        "https://push.example/b": "laptop",
    }


# ---------------------------------------------------------------------------
# Dispatcher tests
# ---------------------------------------------------------------------------


def test_dispatch_without_transport_documents_missing_backend(monkeypatch):
    sub = _make_sub()
    monkeypatch.setattr(
        "cas_forex.push_notifications._resolve_default_transport",
        lambda: (None, DISPATCH_BACKEND_MISSING_MESSAGE),
    )
    result = dispatch_test_push(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Observational test"},
        transport=None,
    )

    assert isinstance(result, PushDispatchResult)
    assert result.endpoint == sub.endpoint
    assert result.success is False
    assert result.status_code is None
    assert result.error_message == DISPATCH_BACKEND_MISSING_MESSAGE


def test_dispatch_without_transport_documents_missing_vapid_config(monkeypatch):
    sub = _make_sub()
    monkeypatch.setattr(
        "cas_forex.push_notifications._resolve_default_transport",
        lambda: (None, DISPATCH_CONFIG_MISSING_MESSAGE),
    )

    result = dispatch_test_push(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Observational test"},
        transport=None,
    )

    assert result.success is False
    assert result.error_message == DISPATCH_CONFIG_MISSING_MESSAGE


def test_dispatch_uses_injected_transport_result():
    sub = _make_sub()
    captured: list = []

    def fake_transport(subscription, payload):
        captured.append((subscription.endpoint, payload))
        return PushDispatchResult(
            endpoint=subscription.endpoint,
            success=True,
            status_code=201,
            error_message=None,
        )

    result = dispatch_test_push(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Trade executed (observational)"},
        transport=fake_transport,
    )

    assert result.success is True
    assert result.status_code == 201
    assert captured == [
        (sub.endpoint, {"title": "CAS Forex", "body": "Trade executed (observational)"})
    ]


def test_dispatch_without_injected_transport_uses_resolved_default_transport(monkeypatch):
    sub = _make_sub()
    captured: list = []

    def fake_transport(subscription, payload):
        captured.append((subscription.endpoint, payload))
        return PushDispatchResult(
            endpoint=subscription.endpoint,
            success=True,
            status_code=202,
            error_message=None,
        )

    monkeypatch.setattr(
        "cas_forex.push_notifications._resolve_default_transport",
        lambda: (fake_transport, None),
    )

    result = dispatch_test_push(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Loop resumed (observational)"},
        transport=None,
    )

    assert result.success is True
    assert result.status_code == 202
    assert captured == [
        (sub.endpoint, {"title": "CAS Forex", "body": "Loop resumed (observational)"})
    ]


def test_dispatch_rejects_advisory_payload():
    sub = _make_sub()
    with pytest.raises(ValueError):
        dispatch_test_push(
            subscription=sub,
            payload={"title": "Hot tip", "body": "You should buy EURUSD now"},
            transport=None,
        )
