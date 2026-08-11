from __future__ import annotations

import asyncio

from api.routes import external_monitoring as route_module
from cas_forex.external_monitoring_control import (
    build_external_monitoring_control_report,
    set_override_path_for_tests,
    set_external_monitoring_overrides,
)


def test_external_monitoring_update_encrypts_runtime_values(tmp_path, monkeypatch):
    override_path = tmp_path / "runtime" / "external-monitoring-overrides.json"
    set_override_path_for_tests(override_path)
    monkeypatch.setattr(
        route_module,
        "build_external_monitoring_readiness",
        lambda *args, **kwargs: {"report_kind": "cas_forex_external_monitoring_readiness", "status": "OK"},
    )
    monkeypatch.setattr(
        route_module,
        "build_operational_readiness_report",
        lambda *args, **kwargs: {"report_kind": "cas_forex_operational_readiness", "status": "OK"},
    )
    monkeypatch.setattr(
        route_module,
        "build_professional_readiness_matrix",
        lambda *args, **kwargs: {"report_kind": "cas_forex_professional_readiness_matrix", "status": "ATTENTION"},
    )
    monkeypatch.setattr(
        route_module,
        "build_public_launch_gate",
        lambda *args, **kwargs: {"report_kind": "cas_forex_public_launch_gate", "status": "ATTENTION"},
    )
    try:
        body = asyncio.run(
            route_module.update_external_monitoring(
                route_module.ExternalMonitoringUpdate(
                    uptime_monitor_url="https://healthchecks.example/ping/runtime",
                    error_tracking_dsn="https://public:secret@sentry.example/42",
                    alert_webhook_url="https://hooks.example/runtime/critical",
                )
            )
        )
        persisted = override_path.read_text(encoding="utf-8")
    finally:
        set_override_path_for_tests(None)

    assert body["status"] == "UPDATED"
    assert body["applied_keys"] == ["uptime_monitor_url", "error_tracking_dsn", "alert_webhook_url"]
    assert "healthchecks.example" not in persisted
    assert "sentry.example" not in persisted
    assert "hooks.example" not in persisted
    assert '"encrypted": true' in persisted.lower()


def test_external_monitoring_reset_clears_runtime_values(tmp_path, monkeypatch):
    override_path = tmp_path / "runtime" / "external-monitoring-overrides.json"
    set_override_path_for_tests(override_path)
    set_external_monitoring_overrides(
        uptime_monitor_url="https://healthchecks.example/ping/runtime",
        error_tracking_dsn="https://public:secret@sentry.example/42",
        alert_webhook_url="https://hooks.example/runtime/critical",
    )
    monkeypatch.setattr(
        route_module,
        "build_external_monitoring_readiness",
        lambda *args, **kwargs: {"report_kind": "cas_forex_external_monitoring_readiness", "status": "ATTENTION"},
    )
    monkeypatch.setattr(
        route_module,
        "build_operational_readiness_report",
        lambda *args, **kwargs: {"report_kind": "cas_forex_operational_readiness", "status": "ATTENTION"},
    )
    monkeypatch.setattr(
        route_module,
        "build_professional_readiness_matrix",
        lambda *args, **kwargs: {"report_kind": "cas_forex_professional_readiness_matrix", "status": "ATTENTION"},
    )
    monkeypatch.setattr(
        route_module,
        "build_public_launch_gate",
        lambda *args, **kwargs: {"report_kind": "cas_forex_public_launch_gate", "status": "ATTENTION"},
    )
    try:
        body = asyncio.run(route_module.reset_external_monitoring())
        control = build_external_monitoring_control_report()
    finally:
        set_override_path_for_tests(None)

    assert body["status"] == "RESET"
    assert sorted(body["applied_keys"]) == ["alert_webhook_url", "error_tracking_dsn", "uptime_monitor_url"]
    assert override_path.exists() is False
    assert control["uptime_monitor"]["configured"] is False
    assert control["error_tracking_dsn"]["configured"] is False
    assert control["alert_destination"]["configured"] is False
