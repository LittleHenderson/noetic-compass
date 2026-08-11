from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.backup_restore import BackupManifest, create_backup
from cas_forex.operational_readiness import build_operational_readiness_report
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_core_operational_files(root: Path) -> None:
    for rel in (
        "api/routes/system_health.py",
        "api/routes/stack_health.py",
        "api/routes/webhook_notifications.py",
        "api/server.py",
        "cas_forex/critical_notifications.py",
        "cas_forex/system_health_monitor.py",
        "cas_forex/stack_health_check.py",
        "cas_forex/backup_restore.py",
        "tests/test_backup_restore.py",
        "docs/MOBILE_APP.md",
        "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md",
        "ui/dist/index.html",
        "runtime/api-request-trace.jsonl",
        "runtime/worker-logs/worker.log",
        "strategy_leads.json",
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
            "health logs backup restore rollback previous build\n"
            "settings\n"
            "CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example\n"
            "External Monitoring CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL "
            "CAS_FOREX_ERROR_TRACKING_DSN SENTRY_DSN\n"
        ),
    )
    create_backup(
        repo_root=root,
        snapshot_dir=root / "runtime" / "backups",
        file_patterns=("strategy_leads.json",),
        now=datetime(2026, 7, 8, tzinfo=timezone.utc),
    )


def test_operational_readiness_ok_when_core_evidence_exists(tmp_path):
    _write_core_operational_files(tmp_path)

    report = build_operational_readiness_report(
        tmp_path,
        env={
            "CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL": "https://healthchecks.example/ping",
            "CAS_FOREX_ERROR_TRACKING_DSN": "https://public:private@sentry.example/42",
            "CAS_FOREX_ALERT_WEBHOOK_URL": "https://hooks.example/critical",
        },
        notification_readiness={
            "status": "DELIVERY_CONFIRMED",
            "offscreen_destination_count": 1,
            "blockers": [],
            "next_action": "Critical notification delivery has a recent successful webhook attempt.",
        },
    )

    assert report["report_kind"] == "cas_forex_operational_readiness"
    assert report["status"] == "OK"
    assert report["attention_count"] == 0
    assert report["top_attention_items"] == []
    assert report["next_action"] == "Operational readiness checks pass."
    assert report["backup_inventory"]["snapshot_count"] == 1
    assert report["backup_inventory"]["latest_snapshot"]["file_count"] == 1
    assert report["external_monitoring"]["status"] == "OK"
    assert report["external_monitoring"]["deployment_handoff"]["status"] == "READY"
    assert all(check["status"] == "OK" for check in report["checks"])


def test_operational_readiness_surfaces_backup_and_runbook_gaps(tmp_path):
    _write(tmp_path / "api/routes/system_health.py")
    _write(tmp_path / "api/routes/stack_health.py")

    report = build_operational_readiness_report(tmp_path)

    assert report["status"] == "ATTENTION"
    assert report["top_attention_items"]
    assert report["next_action"] == report["top_attention_items"][0]
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["backup_snapshots"]["status"] == "ATTENTION"
    assert checks["operations_runbook"]["status"] == "MISSING"
    assert checks["rollback_runbook"]["status"] == "MISSING"
    assert report["attention_items"]


def test_operational_readiness_surfaces_external_monitoring_action_when_core_files_exist(tmp_path):
    _write_core_operational_files(tmp_path)

    report = build_operational_readiness_report(tmp_path, env={})

    assert report["status"] == "ATTENTION"
    assert report["next_action"] == "Configure one of the external uptime monitor URL env vars."
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["external_monitoring"]["status"] == "ATTENTION"
    assert checks["external_monitoring"]["detail"] == "Configure one of the external uptime monitor URL env vars."
    assert report["external_monitoring"]["deployment_handoff"]["status"] == "ACTION_REQUIRED"
    assert "curl -fsS https://your-cas-forex-host/health" in report["external_monitoring"]["deployment_handoff"]["verification_commands"]


def test_operational_readiness_route_is_cache_first_and_read_only(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(settings_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(settings_route.get_operational_readiness())

    assert captured == {
        "key": "settings_operational_readiness",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_operational_readiness"
    assert body["status"] == "WARMING"
    assert body["external_monitoring"]["status"] == "WARMING"
    assert "restore backups" in body["claim_boundary"]


def test_operator_backup_create_route_returns_manifest_and_fresh_readiness(monkeypatch):
    def fake_create_backup(*, repo_root, snapshot_dir):
        return BackupManifest(
            snapshot_id="abc123",
            created_at_iso="2026-07-08T00:00:00Z",
            repo_root=str(repo_root),
            snapshot_path=str(Path(snapshot_dir) / "cas-forex-backup-test.zip"),
            file_count=2,
            total_bytes=123,
            files=tuple(),
        )

    monkeypatch.setattr(settings_route, "create_backup", fake_create_backup)
    monkeypatch.setattr(
        settings_route,
        "build_operational_readiness_report",
        lambda: {"report_kind": "cas_forex_operational_readiness", "status": "OK"},
    )

    body = asyncio.run(settings_route.post_operator_backup_create())

    assert body["report_kind"] == "cas_forex_operator_backup_create"
    assert body["status"] == "CREATED"
    assert body["manifest"]["snapshot_id"] == "abc123"
    assert body["manifest"]["file_count"] == 2
    assert body["operational_readiness"]["status"] == "OK"
    assert "does not restore files" in body["claim_boundary"]


def test_operational_readiness_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("OperationalReadinessPanel")
    # Moved to components/settings/LegalGovernancePanels.tsx in the settings decomposition.
    extracted_legalgovernancepanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "LegalGovernancePanels.tsx").read_text(encoding="utf-8")
    assert "Operational Readiness" in extracted_legalgovernancepanels
    assert "fetchOperationalReadiness" in extracted_legalgovernancepanels
    assert "createOperatorBackup" in extracted_legalgovernancepanels
    assert "Create operator backup" in extracted_legalgovernancepanels
    assert "External Monitoring" in extracted_legalgovernancepanels
    assert "Deployment Handoff" in extracted_legalgovernancepanels
    assert "Hosted Handoff" in extracted_legalgovernancepanels
    assert "Public Base" in extracted_legalgovernancepanels
    assert "Health Endpoints" in extracted_legalgovernancepanels
    assert "https://your-cas-forex-host" in extracted_legalgovernancepanels
    assert "Save external hooks" in extracted_legalgovernancepanels
    assert "Reset runtime hooks" in extracted_legalgovernancepanels
    # Moved to components/settings/AuditPanels.tsx in the settings decomposition.
    extracted_auditpanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "AuditPanels.tsx").read_text(encoding="utf-8")
    assert "Send critical alert test" in extracted_auditpanels
    assert "Off-screen alert webhook URL" in extracted_legalgovernancepanels
    assert "alert_webhook_url" in extracted_legalgovernancepanels
    assert "updateExternalMonitoringConfig" in extracted_legalgovernancepanels
    assert "resetExternalMonitoringConfig" in extracted_legalgovernancepanels
    assert "testCriticalNotificationDelivery" in extracted_auditpanels
    assert "external_monitoring" in api_client
    assert "ExternalMonitoringReadiness" in api_client
    assert "ExternalMonitoringDeploymentHandoff" in api_client
    assert "deployment_handoff" in api_client
    assert "verification_commands" in api_client
    assert "ExternalMonitoringConfigResult" in api_client
    assert "CriticalNotificationTestResult" in api_client
    assert "OperationalReadinessReport" in api_client
    assert "OperatorBackupCreateResult" in api_client
    assert '"/settings/operational-readiness"' in api_client
    assert '"/settings/operator-backup/create"' in api_client
    assert '"/external-monitoring/update"' in api_client
    assert '"/external-monitoring/reset"' in api_client
    assert '"/webhook-notifications/critical-test"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/operational-readiness") is False
