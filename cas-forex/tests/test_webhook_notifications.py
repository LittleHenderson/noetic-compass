"""Unit tests for the webhook-notification chassis.

Covers the file-backed JSONL subscription store and the pure
``dispatch_webhook`` dispatcher. The observational guard against
trade-advisory payloads is exercised explicitly — that's the
load-bearing safety property of this slice.
"""

from __future__ import annotations

import json

from cas_forex.webhook_notifications import (
    ADVISORY_PHRASE_ERROR_MESSAGE,
    OBSERVATIONAL_GUARD_PHRASES,
    WebhookDispatchResult,
    WebhookSubscription,
    WebhookSubscriptionStore,
    build_webhook_subscription,
    dispatch_webhook,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _store(tmp_path) -> WebhookSubscriptionStore:
    return WebhookSubscriptionStore(path=tmp_path / "subscriptions.jsonl")


def _make_sub(
    url: str = "https://hooks.example/services/AAA/BBB",
    label: str = "slack-alerts",
) -> WebhookSubscription:
    return build_webhook_subscription(webhook_url=url, label=label)


class _StubResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


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
    assert listed[0].webhook_url == sub.webhook_url
    assert listed[0].label == "slack-alerts"


def test_add_duplicate_url_replaces_record(tmp_path):
    # URL is the dedupe key — second add with same URL replaces the first.
    store = _store(tmp_path)
    store.add(_make_sub(label="slack-old"))
    store.add(_make_sub(label="slack-new"))

    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0].label == "slack-new"


def test_remove_returns_true_for_existing_url(tmp_path):
    store = _store(tmp_path)
    sub = _make_sub()
    store.add(sub)

    assert store.remove(sub.webhook_url) is True
    assert store.list_all() == []


def test_remove_accepts_subscription_id(tmp_path):
    store = _store(tmp_path)
    sub = _make_sub()
    store.add(sub)

    assert store.remove(sub.subscription_id) is True
    assert store.list_all() == []


def test_remove_returns_false_when_url_absent(tmp_path):
    store = _store(tmp_path)
    assert store.remove("https://hooks.example/never-added") is False


def test_update_last_used_updates_in_memory_and_persisted_record(tmp_path):
    store_path = tmp_path / "subscriptions.jsonl"
    store = WebhookSubscriptionStore(path=store_path)
    sub = _make_sub(url="https://hooks.example/X/Y")
    store.add(sub)

    when = "2026-06-25T12:00:00+00:00"
    assert store.update_last_used(sub.webhook_url, when) is True

    listed = store.list_all()
    assert len(listed) == 1
    assert listed[0].last_used_at_iso == when

    # And a fresh store instance reading the same file sees the update.
    reopened = WebhookSubscriptionStore(path=store_path)
    again = reopened.list_all()
    assert again[0].last_used_at_iso == when


def test_update_last_used_returns_false_when_url_absent(tmp_path):
    store = _store(tmp_path)
    assert store.update_last_used("https://hooks.example/missing", "now") is False


def test_update_last_used_accepts_subscription_id(tmp_path):
    store = _store(tmp_path)
    sub = _make_sub(url="https://hooks.example/sub-id")
    store.add(sub)

    when = "2026-06-25T12:00:00+00:00"
    assert store.update_last_used(sub.subscription_id, when) is True
    assert store.list_all()[0].last_used_at_iso == when


def test_clear_empties_store(tmp_path):
    store = _store(tmp_path)
    store.add(_make_sub(url="https://hooks.example/a"))
    store.add(_make_sub(url="https://hooks.example/b"))
    assert len(store.list_all()) == 2

    store.clear()
    assert store.list_all() == []


def test_atomic_write_then_read_roundtrip_persists_to_disk(tmp_path):
    store_path = tmp_path / "subscriptions.jsonl"
    store = WebhookSubscriptionStore(path=store_path)
    sub = _make_sub(url="https://hooks.example/persist", label="discord-alerts")
    store.add(sub)

    assert store_path.exists()
    persisted = store_path.read_text(encoding="utf-8")
    lines = [line for line in persisted.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "https://hooks.example/persist" not in persisted
    assert '"encrypted": true' in persisted.lower()
    decoded = json.loads(lines[0])
    assert isinstance(decoded["webhook_url"], dict)
    assert decoded["webhook_url"]["encrypted"] is True
    assert decoded["label"] == "discord-alerts"

    reopened = WebhookSubscriptionStore(path=store_path)
    listed = reopened.list_all()
    assert len(listed) == 1
    assert listed[0].webhook_url == "https://hooks.example/persist"


def test_legacy_plaintext_webhook_url_is_migrated_to_encrypted(tmp_path):
    store_path = tmp_path / "subscriptions.jsonl"
    store_path.write_text(
        json.dumps(
            {
                "webhook_url": "https://hooks.example/legacy",
                "label": "legacy-alerts",
                "created_at_iso": "2026-07-09T00:00:00+00:00",
                "last_used_at_iso": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    store = WebhookSubscriptionStore(path=store_path)
    listed = store.list_all()

    assert len(listed) == 1
    assert listed[0].webhook_url == "https://hooks.example/legacy"
    assert listed[0].label == "legacy-alerts"

    rewritten = store_path.read_text(encoding="utf-8")
    assert "https://hooks.example/legacy" not in rewritten
    assert '"encrypted": true' in rewritten.lower()


# ---------------------------------------------------------------------------
# Dispatcher tests
# ---------------------------------------------------------------------------


def test_dispatch_with_injected_transport_returns_success_on_200():
    sub = _make_sub()
    captured: list = []

    def fake_transport(url, json, headers, timeout):
        captured.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return _StubResponse(200, text="ok")

    result = dispatch_webhook(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Trade executed (observational)."},
        transport=fake_transport,
    )

    assert isinstance(result, WebhookDispatchResult)
    assert result.success is True
    assert result.status_code == 200
    assert result.error_message is None
    assert result.response_snippet == "ok"

    # Transport saw the expected POST shape.
    assert len(captured) == 1
    assert captured[0]["url"] == sub.webhook_url
    assert captured[0]["json"] == {
        "title": "CAS Forex",
        "body": "Trade executed (observational).",
    }
    assert captured[0]["headers"] == {"Content-Type": "application/json"}
    assert captured[0]["timeout"] == 10.0


def test_dispatch_refuses_advisory_payload_and_never_sends():
    sub = _make_sub()
    transport_calls: list = []

    def transport_should_not_be_called(*_args, **_kwargs):
        transport_calls.append("called")
        return _StubResponse(200)

    result = dispatch_webhook(
        subscription=sub,
        payload={"title": "Hot tip", "body": "You should buy EURUSD now"},
        transport=transport_should_not_be_called,
    )

    assert result.success is False
    assert result.status_code is None
    assert result.error_message is not None
    assert ADVISORY_PHRASE_ERROR_MESSAGE in result.error_message
    # Critically: transport was NEVER invoked. The guard is enforced
    # BEFORE any HTTP attempt.
    assert transport_calls == []


def test_dispatch_with_http_500_returns_failure_with_status():
    sub = _make_sub()

    def fake_transport(url, json, headers, timeout):
        return _StubResponse(500, text="internal server error")

    result = dispatch_webhook(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Loop stalled (observational)."},
        transport=fake_transport,
    )

    assert result.success is False
    assert result.status_code == 500
    assert result.error_message is not None
    assert "non-success" in result.error_message
    assert result.response_snippet == "internal server error"


def test_dispatch_with_raising_transport_documents_failure():
    sub = _make_sub()

    class _Boom(RuntimeError):
        pass

    def fake_transport(url, json, headers, timeout):
        raise _Boom("connection refused")

    result = dispatch_webhook(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Test (observational)."},
        transport=fake_transport,
    )

    assert result.success is False
    assert result.status_code is None
    assert result.error_message is not None
    assert "transport raised" in result.error_message
    assert "connection refused" in result.error_message


def test_dispatch_response_snippet_is_truncated_to_200_chars():
    sub = _make_sub()
    long_text = "x" * 500

    def fake_transport(url, json, headers, timeout):
        return _StubResponse(201, text=long_text)

    result = dispatch_webhook(
        subscription=sub,
        payload={"title": "CAS Forex", "body": "Observational."},
        transport=fake_transport,
    )

    assert result.success is True
    assert result.response_snippet is not None
    assert len(result.response_snippet) == 200


def test_every_guard_phrase_is_caught_in_body():
    sub = _make_sub()
    transport_calls: list = []

    def transport_should_not_be_called(*_args, **_kwargs):
        transport_calls.append("called")
        return _StubResponse(200)

    for phrase in OBSERVATIONAL_GUARD_PHRASES:
        result = dispatch_webhook(
            subscription=sub,
            payload={"title": "CAS Forex", "body": f"prefix {phrase} suffix"},
            transport=transport_should_not_be_called,
        )
        assert result.success is False, f"guard phrase {phrase!r} slipped through"
        assert result.error_message is not None
        assert ADVISORY_PHRASE_ERROR_MESSAGE in result.error_message

    assert transport_calls == []
