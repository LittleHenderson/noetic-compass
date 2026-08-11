from __future__ import annotations

import json

from cas_forex import push_delivery_control


def test_push_delivery_report_without_backend_or_config(monkeypatch):
    monkeypatch.setattr(
        push_delivery_control,
        "probe_push_delivery_backend",
        lambda: {"available": False, "package": "pywebpush", "version": None},
    )
    report = push_delivery_control.build_push_delivery_backend_report(subscription_count=0)

    assert report["report_kind"] == "cas_forex_push_delivery_backend"
    assert report["status"] == "BACKEND_MISSING"
    assert report["dispatch_backend_available"] is False
    assert report["subscription_registration_ready"] is False
    assert report["dispatch_ready"] is False
    assert report["fully_ready"] is False
    assert "pywebpush" in " ".join(report["blockers"])


def test_push_delivery_runtime_overrides_are_encrypted_and_reported(tmp_path, monkeypatch):
    override_path = tmp_path / "push-delivery-overrides.json"
    push_delivery_control.set_override_path_for_tests(override_path)
    monkeypatch.setattr(
        push_delivery_control,
        "probe_push_delivery_backend",
        lambda: {"available": True, "package": "pywebpush", "version": "2.3.0"},
    )
    changed: list[str]
    persisted: str
    report: dict
    try:
        changed = push_delivery_control.set_push_delivery_overrides(
            vapid_public_key="PUBLIC_KEY_1234567890",
            vapid_private_key="PRIVATE_KEY_0987654321",
            vapid_subject="mailto:owner@example.com",
        )
        persisted = override_path.read_text(encoding="utf-8")
        report = push_delivery_control.build_push_delivery_backend_report(subscription_count=1)
    finally:
        push_delivery_control.clear_push_delivery_overrides()
        push_delivery_control.set_override_path_for_tests(None)

    assert sorted(changed) == [
        "vapid_private_key",
        "vapid_public_key",
        "vapid_subject",
    ]
    assert "PUBLIC_KEY_1234567890" not in persisted
    assert "PRIVATE_KEY_0987654321" not in persisted
    assert "owner@example.com" not in persisted
    assert '"encrypted": true' in persisted.lower()

    payload = json.dumps(report, sort_keys=True)
    assert "PRIVATE_KEY_0987654321" not in payload
    assert report["dispatch_backend_available"] is True
    assert report["subscription_registration_ready"] is True
    assert report["dispatch_ready"] is True
    assert report["fully_ready"] is True
    assert report["vapid_public_key"] == "PUBLIC_KEY_1234567890"
    assert report["vapid_private_key"]["configured"] is True
    assert report["vapid_private_key"]["source"] == "runtime_override"
    assert report["vapid_subject"]["value"] == "mailto:owner@example.com"
