from __future__ import annotations

from pathlib import Path

from cas_forex.external_monitoring_control import (
    set_external_monitoring_overrides,
    set_override_path_for_tests,
)
from cas_forex.external_monitoring import build_external_monitoring_readiness


def _write(path: Path, text: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_monitoring_files(root: Path) -> None:
    for rel in (
        "api/routes/system_health.py",
        "api/routes/stack_health.py",
        "api/server.py",
        "cas_forex/critical_notifications.py",
        "api/routes/webhook_notifications.py",
    ):
        _write(root / rel)
    _write(
        root / "docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example",
        (
            "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL=https://healthchecks.example/ping/runtime\n"
            "CAS_FOREX_ERROR_TRACKING_DSN=https://public:secret@sentry.example/42\n"
            "CAS_FOREX_ALERT_WEBHOOK_URL=https://hooks.example/services/cas-forex-critical\n"
        ),
    )
    _write(
        root / "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
        (
            "External Monitoring\n"
            "Settings\n"
            "CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example\n"
            "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL\n"
            "CAS_FOREX_ERROR_TRACKING_DSN\n"
            "SENTRY_DSN\n"
        ),
    )


def test_external_monitoring_ready_when_deployment_hooks_are_configured(tmp_path):
    _write_monitoring_files(tmp_path)

    report = build_external_monitoring_readiness(
        tmp_path,
        env={
            "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL": "https://healthchecks.example/ping/abc",
            "CAS_FOREX_ERROR_TRACKING_DSN": "https://public:secret@sentry.example/42",
            "CAS_FOREX_ALERT_WEBHOOK_URL": "https://hooks.example/services/abc",
        },
        notification_readiness={
            "status": "DELIVERY_CONFIRMED",
            "offscreen_destination_count": 1,
            "blockers": [],
            "next_action": "Critical notification delivery has a recent successful webhook attempt.",
        },
    )

    assert report["report_kind"] == "cas_forex_external_monitoring_readiness"
    assert report["status"] == "OK"
    assert report["attention_count"] == 0
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["external_uptime_monitor"]["configured_key"] == "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL"
    assert checks["external_uptime_monitor"]["masked_value"] == "https://healthchecks.example/..."
    assert checks["error_tracking_dsn"]["masked_value"].startswith("http")
    assert "secret" not in str(report)
    assert "/api/forex/stack-health/check" in report["health_endpoints"]
    assert report["deployment_handoff"]["status"] == "READY"
    assert report["deployment_handoff"]["attention_keys"] == []
    assert "curl -fsS https://your-cas-forex-host/health" in report["deployment_handoff"]["verification_commands"]
    assert "/api/forex/stack-health/check" in report["deployment_handoff"]["health_endpoints"]
    assert any(
        doc["path"].endswith("CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example") and doc["present"] is True
        for doc in report["deployment_handoff"]["package_documents"]
    )
    assert any("Copy docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example" in step for step in report["deployment_handoff"]["setup_steps"])
    assert "does not ping external services" in report["deployment_handoff"]["claim_boundary"]


def test_external_monitoring_reports_deployment_attention_without_hooks(tmp_path):
    _write_monitoring_files(tmp_path)

    report = build_external_monitoring_readiness(tmp_path, env={})

    assert report["status"] == "ATTENTION"
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["monitoring_source_surfaces"]["status"] == "OK"
    assert checks["external_uptime_monitor"]["status"] == "MISSING"
    assert checks["error_tracking_dsn"]["status"] == "MISSING"
    assert checks["offscreen_alert_destination"]["status"] == "ATTENTION"
    assert report["top_attention_items"]
    handoff = report["deployment_handoff"]
    assert handoff["status"] == "ACTION_REQUIRED"
    assert "external_uptime_monitor" in handoff["attention_keys"]
    assert handoff["owner_ui_path"] == "?page=settings"
    assert handoff["public_base_url_placeholder"] == "https://your-cas-forex-host"
    assert any(
        doc["path"].endswith("CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example")
        for doc in handoff["package_documents"]
    )
    assert handoff["required_env"]["uptime_monitor_any_of"][0] == "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL"
    assert any("Configure CAS_FOREX_ERROR_TRACKING_DSN" in step for step in handoff["setup_steps"])


def test_external_monitoring_reports_missing_runbook_terms(tmp_path):
    _write(tmp_path / "api/routes/system_health.py")
    _write(tmp_path / "api/routes/stack_health.py")
    _write(tmp_path / "api/server.py")
    _write(tmp_path / "cas_forex/critical_notifications.py")
    _write(tmp_path / "api/routes/webhook_notifications.py")
    _write(tmp_path / "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md", "health only\n")
    _write(
        tmp_path / "docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example",
        "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL=\nCAS_FOREX_ERROR_TRACKING_DSN=\nCAS_FOREX_ALERT_WEBHOOK_URL=\n",
    )

    report = build_external_monitoring_readiness(
        tmp_path,
        env={
            "CAS_FOREX_UPTIME_MONITOR_URL": "https://uptime.example/check",
            "SENTRY_DSN": "dsn-secret-value",
            "CAS_FOREX_CRITICAL_WEBHOOK_URL": "https://hooks.example/critical",
        },
        notification_readiness={
            "status": "CONFIGURED_NOT_TESTED",
            "offscreen_destination_count": 1,
            "blockers": ["Webhook destination exists, but no recent critical notification delivery attempt is recorded."],
            "next_action": "Send a critical alert test and verify delivery before relying on off-screen alerts.",
        },
    )

    checks = {check["key"]: check for check in report["checks"]}
    assert report["status"] == "ATTENTION"
    assert checks["external_monitoring_runbook"]["status"] == "MISSING"
    assert "cas_forex_error_tracking_dsn" in checks["external_monitoring_runbook"]["missing_terms"]


def test_external_monitoring_accepts_runtime_overrides_and_webhook_destinations(tmp_path):
    _write_monitoring_files(tmp_path)
    override_path = tmp_path / "runtime" / "external-monitoring-overrides.json"
    set_override_path_for_tests(override_path)
    try:
        set_external_monitoring_overrides(
            uptime_monitor_url="https://healthchecks.example/ping/runtime",
            error_tracking_dsn="https://public:secret@sentry.example/42",
            alert_webhook_url="https://hooks.example/runtime/critical",
        )
        report = build_external_monitoring_readiness(
            tmp_path,
            env={},
            notification_readiness={
                "status": "DELIVERY_CONFIRMED",
                "offscreen_destination_count": 1,
                "blockers": [],
                "next_action": "Critical notification delivery has a recent successful webhook attempt.",
            },
        )
    finally:
        set_override_path_for_tests(None)

    checks = {check["key"]: check for check in report["checks"]}
    assert report["status"] == "OK"
    assert checks["external_uptime_monitor"]["configured_key"] == "runtime_override"
    assert checks["external_uptime_monitor"]["masked_value"] == "https://healthchecks.example/..."
    assert checks["error_tracking_dsn"]["configured_key"] == "runtime_override"
    assert checks["offscreen_alert_destination"]["configured_key"] == "runtime_override"
    assert checks["offscreen_alert_destination"]["masked_value"] == "https://hooks.example/..."


def test_external_monitoring_marks_offscreen_destination_attention_until_delivery_is_confirmed(tmp_path):
    _write_monitoring_files(tmp_path)

    report = build_external_monitoring_readiness(
        tmp_path,
        env={
            "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL": "https://healthchecks.example/ping/abc",
            "CAS_FOREX_ERROR_TRACKING_DSN": "https://public:secret@sentry.example/42",
            "CAS_FOREX_ALERT_WEBHOOK_URL": "https://hooks.example/services/abc",
        },
        notification_readiness={
            "status": "CONFIGURED_NOT_TESTED",
            "offscreen_destination_count": 1,
            "blockers": ["Webhook destination exists, but no recent critical notification delivery attempt is recorded."],
            "next_action": "Send a critical alert test and verify delivery before relying on off-screen alerts.",
        },
    )

    checks = {check["key"]: check for check in report["checks"]}
    assert report["status"] == "ATTENTION"
    assert checks["offscreen_alert_destination"]["status"] == "ATTENTION"
    assert "critical alert test" in checks["offscreen_alert_destination"]["detail"].lower()
