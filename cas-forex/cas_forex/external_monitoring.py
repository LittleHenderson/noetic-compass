"""External uptime/error-monitoring readiness for CAS Forex.

This is deliberately read-only. It checks whether deployment-time hooks for
off-machine monitoring are configured and whether the repo exposes the health,
error-trace, and alert surfaces a monitor should watch.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from cas_forex.critical_notifications import build_critical_notification_delivery_readiness
from cas_forex.external_monitoring_control import (
    ALERT_WEBHOOK_ENV_KEYS,
    ALERT_WEBHOOK_URL_KEY,
    ERROR_TRACKING_ENV_KEYS,
    UPTIME_ENV_KEYS,
    resolve_external_monitoring_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_external_monitoring_readiness"
OPERATIONS_RUNBOOK = Path("docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md")
ENV_TEMPLATE_PATH = Path("docs/operations/CAS_FOREX_EXTERNAL_MONITORING_ENV_TEMPLATE.env.example")

HEALTH_ENDPOINTS = (
    "/health",
    "/api/forex/health",
    "/api/forex/stack-health/check",
    "/api/forex/system-health/snapshot",
)

CLAIM_BOUNDARY = (
    "External monitoring readiness is a read-only deployment diagnostic. It "
    "masks configured URLs/DSNs and does not ping external services, send "
    "alerts, place orders, close positions, move money, or authorize live "
    "trading."
)


def build_external_monitoring_readiness(
    root: Path | str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    notification_readiness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    env_map = dict(os.environ if env is None else env)
    resolved = resolve_external_monitoring_config(env_map)
    delivery = dict(notification_readiness or build_critical_notification_delivery_readiness(limit=5, env=env_map))
    checks = [
        _source_surface_check(base),
        _resolved_config_check(
            "external_uptime_monitor",
            "External Uptime Monitor",
            UPTIME_ENV_KEYS,
            resolved.get("uptime_monitor_url") or {},
            "Off-machine uptime/heartbeat monitor endpoint is configured.",
            "Configure one of the external uptime monitor URL env vars.",
        ),
        _resolved_config_check(
            "error_tracking_dsn",
            "Error Tracking DSN",
            ERROR_TRACKING_ENV_KEYS,
            resolved.get("error_tracking_dsn") or {},
            "External error-tracking DSN is configured.",
            "Configure CAS_FOREX_ERROR_TRACKING_DSN or SENTRY_DSN before hosted production.",
        ),
        _offscreen_alert_check(resolved, env_map, delivery),
        _runbook_check(base),
        _env_template_check(base),
    ]
    attention = [check for check in checks if check["status"] != "OK"]
    required_env = {
        "uptime_monitor_any_of": list(UPTIME_ENV_KEYS),
        "error_tracking_any_of": list(ERROR_TRACKING_ENV_KEYS),
        "alert_destination_any_of": list(ALERT_WEBHOOK_ENV_KEYS),
    }
    return {
        "report_kind": REPORT_KIND,
        "status": "OK" if not attention else "ATTENTION",
        "ok_count": sum(1 for check in checks if check["status"] == "OK"),
        "attention_count": len(attention),
        "checks": checks,
        "health_endpoints": list(HEALTH_ENDPOINTS),
        "required_env": required_env,
        "deployment_handoff": _deployment_handoff(
            checks=checks,
            required_env=required_env,
            attention=attention,
        ),
        "top_attention_items": [check["detail"] for check in attention][:6],
        "next_action": (
            "External uptime, error tracking, and alert hooks are configured."
            if not attention
            else str([check["detail"] for check in attention if str(check.get("detail") or "").strip()][:1][0])
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _deployment_handoff(
    *,
    checks: list[dict[str, Any]],
    required_env: Mapping[str, list[str]],
    attention: list[dict[str, Any]],
) -> dict[str, Any]:
    check_statuses = {
        str(check.get("key") or ""): str(check.get("status") or "UNKNOWN")
        for check in checks
        if check.get("key")
    }
    attention_keys = [
        str(check.get("key") or "")
        for check in attention
        if str(check.get("key") or "").strip()
    ]
    handoff = {
        "status": "READY" if not attention else "ACTION_REQUIRED",
        "public_base_url_placeholder": "https://your-cas-forex-host",
        "owner_ui_path": "?page=settings",
        "health_endpoints": list(HEALTH_ENDPOINTS),
        "required_env": dict(required_env),
        "attention_keys": attention_keys,
        "check_statuses": check_statuses,
        "package_documents": [
            {
                "path": OPERATIONS_RUNBOOK.as_posix(),
                "present": OPERATIONS_RUNBOOK.exists(),
                "purpose": "Hosted operations runbook with health, env-var, alert, backup, and rollback guidance.",
            },
            {
                "path": ENV_TEMPLATE_PATH.as_posix(),
                "present": ENV_TEMPLATE_PATH.exists(),
                "purpose": "Deployment env template for uptime monitor URL, error-tracking DSN, and alert webhook.",
            },
            {
                "path": "cas_forex/external_monitoring_control.py",
                "present": True,
                "purpose": "Runtime override control surface for masked local monitoring hooks.",
            },
        ],
        "setup_steps": [
            "Deploy CAS Forex behind HTTPS with owner authentication enabled.",
            "Point an off-machine uptime provider at /health or /api/forex/stack-health/check.",
            f"Copy {ENV_TEMPLATE_PATH.as_posix()} into deployment environment management and replace placeholders.",
            "Configure one uptime URL env var or save the hosted heartbeat URL from Settings.",
            "Configure CAS_FOREX_ERROR_TRACKING_DSN or SENTRY_DSN for hosted error tracking.",
            "Configure an off-screen alert webhook and send a critical alert test from Settings.",
            "Reopen Settings > Operational Readiness and confirm External Monitoring is OK.",
        ],
        "verification_commands": [
            "curl -fsS https://your-cas-forex-host/health",
            "curl -fsS https://your-cas-forex-host/api/forex/stack-health/check",
            "python -m pytest tests/test_external_monitoring.py tests/test_operational_readiness.py -q",
        ],
        "claim_boundary": (
            "This handoff is a read-only deployment checklist. It does not ping "
            "external services, send alerts, change configuration, place orders, "
            "move money, or authorize live trading."
        ),
    }
    return handoff


def _source_surface_check(base: Path) -> dict[str, Any]:
    paths = (
        Path("api/routes/system_health.py"),
        Path("api/routes/stack_health.py"),
        Path("api/server.py"),
        Path("cas_forex/critical_notifications.py"),
        Path("api/routes/webhook_notifications.py"),
    )
    evidence = [{"path": path.as_posix(), "present": (base / path).exists()} for path in paths]
    missing = [row["path"] for row in evidence if not row["present"]]
    return {
        "key": "monitoring_source_surfaces",
        "label": "Monitoring Source Surfaces",
        "status": "OK" if not missing else "MISSING",
        "detail": (
            "Health, stack, request trace, critical notification, and webhook surfaces are present."
            if not missing
            else "Monitoring source surfaces are missing."
        ),
        "evidence": evidence,
        "missing_paths": missing,
        "configured_key": None,
        "masked_value": None,
    }


def _env_any_check(
    key: str,
    label: str,
    env_keys: Iterable[str],
    env_map: Mapping[str, str],
    ok_detail: str,
    missing_detail: str,
    *,
    value_kind: str,
    advisory: bool = False,
) -> dict[str, Any]:
    configured_key = ""
    value = ""
    for env_key in env_keys:
        probe = str(env_map.get(env_key, "") or "").strip()
        if probe:
            configured_key = env_key
            value = probe
            break
    configured = bool(configured_key)
    status = "OK" if configured else ("ATTENTION" if advisory else "MISSING")
    return {
        "key": key,
        "label": label,
        "status": status,
        "detail": ok_detail if configured else missing_detail,
        "env_keys": list(env_keys),
        "configured_key": configured_key or None,
        "masked_value": _masked_value(value, value_kind=value_kind) if configured else None,
        "missing_env_keys": [] if configured else list(env_keys),
        "advisory": advisory,
    }


def _resolved_config_check(
    key: str,
    label: str,
    env_keys: Iterable[str],
    resolved: Mapping[str, Any],
    ok_detail: str,
    missing_detail: str,
) -> dict[str, Any]:
    configured = bool(resolved.get("configured"))
    return {
        "key": key,
        "label": label,
        "status": "OK" if configured else "MISSING",
        "detail": ok_detail if configured else missing_detail,
        "env_keys": list(env_keys),
        "configured_key": resolved.get("configured_key"),
        "masked_value": resolved.get("masked_value"),
        "missing_env_keys": [] if configured else list(env_keys),
        "advisory": False,
    }


def _offscreen_alert_check(
    resolved: Mapping[str, Any],
    env_map: Mapping[str, str],
    notification_readiness: Mapping[str, Any],
) -> dict[str, Any]:
    alert_config = dict(resolved.get(ALERT_WEBHOOK_URL_KEY) or {})
    delivery_status = str(notification_readiness.get("status") or "")
    readiness_next_action = str(notification_readiness.get("next_action") or "")
    delivery_blockers = [str(item) for item in (notification_readiness.get("blockers") or []) if item]
    delivery_detail = readiness_next_action or "; ".join(delivery_blockers)
    if bool(alert_config.get("configured")):
        return {
            "key": "offscreen_alert_destination",
            "label": "Off-Screen Alert Destination",
            "status": "OK" if delivery_status == "DELIVERY_CONFIRMED" else "ATTENTION",
            "detail": (
                "Off-screen alert destination is configured and recent delivery is confirmed."
                if delivery_status == "DELIVERY_CONFIRMED"
                else delivery_detail or "Off-screen alert destination is configured but recent delivery is not yet confirmed."
            ),
            "env_keys": list(ALERT_WEBHOOK_ENV_KEYS),
            "configured_key": alert_config.get("configured_key"),
            "masked_value": alert_config.get("masked_value"),
            "missing_env_keys": [],
            "advisory": True,
            "delivery_status": delivery_status,
        }
    env_check = _env_any_check(
        "offscreen_alert_destination",
        "Off-Screen Alert Destination",
        ALERT_WEBHOOK_ENV_KEYS,
        env_map,
        "Off-screen alert destination is configured.",
        "Configure an alert webhook env var or register a webhook destination in Settings.",
        value_kind="url",
        advisory=True,
    )
    if env_check.get("configured_key"):
        env_check["status"] = "OK" if delivery_status == "DELIVERY_CONFIRMED" else "ATTENTION"
        env_check["detail"] = (
            "Off-screen alert destination is configured and recent delivery is confirmed."
            if delivery_status == "DELIVERY_CONFIRMED"
            else delivery_detail or "Off-screen alert destination is configured but recent delivery is not yet confirmed."
        )
        env_check["delivery_status"] = delivery_status
        return env_check
    destination_count = int(notification_readiness.get("offscreen_destination_count") or 0)
    if destination_count > 0:
        return {
            "key": "offscreen_alert_destination",
            "label": "Off-Screen Alert Destination",
            "status": "OK" if delivery_status == "DELIVERY_CONFIRMED" else "ATTENTION",
            "detail": (
                "Off-screen alert destination is configured via webhook subscriptions and recent delivery is confirmed."
                if delivery_status == "DELIVERY_CONFIRMED"
                else delivery_detail or "Off-screen alert destination exists, but recent delivery is not yet confirmed."
            ),
            "env_keys": list(ALERT_WEBHOOK_ENV_KEYS),
            "configured_key": "WEBHOOK_SUBSCRIPTION_STORE",
            "masked_value": f"{destination_count} webhook subscription(s)",
            "missing_env_keys": [],
            "advisory": True,
            "delivery_status": notification_readiness.get("status"),
            "offscreen_destination_count": destination_count,
        }
    return env_check


def _runbook_check(base: Path) -> dict[str, Any]:
    path = OPERATIONS_RUNBOOK
    text = _read_text(base / path).lower()
    terms = (
        "external monitoring",
        "cas_forex_external_uptime_monitor_url",
        "cas_forex_error_tracking_dsn",
        "sentry_dsn",
        "cas_forex_external_monitoring_env_template.env.example",
        "settings",
    )
    missing = [term for term in terms if term not in text]
    return {
        "key": "external_monitoring_runbook",
        "label": "External Monitoring Runbook",
        "status": "OK" if text and not missing else "MISSING",
        "detail": (
            "Operations runbook documents external uptime and error-tracking setup."
            if text and not missing
            else "Document external uptime/error-tracking setup in the operations runbook."
        ),
        "evidence": [{"term": term, "present": term not in missing} for term in terms],
        "missing_terms": missing,
        "missing_paths": [] if text else [path.as_posix()],
    }


def _env_template_check(base: Path) -> dict[str, Any]:
    path = ENV_TEMPLATE_PATH
    text = _read_text(base / path)
    lowered = text.lower()
    terms = (
        "cas_forex_external_uptime_monitor_url",
        "cas_forex_error_tracking_dsn",
        "cas_forex_alert_webhook_url",
    )
    missing = [term for term in terms if term not in lowered]
    return {
        "key": "external_monitoring_env_template",
        "label": "External Monitoring Env Template",
        "status": "OK" if text and not missing else "MISSING",
        "detail": (
            "Hosted monitoring env template exists with uptime, error-tracking, and alert placeholders."
            if text and not missing
            else "Add the hosted monitoring env template with uptime, error-tracking, and alert placeholders."
        ),
        "evidence": [{"term": term, "present": term not in missing} for term in terms],
        "missing_terms": missing,
        "missing_paths": [] if text else [path.as_posix()],
    }


def _masked_value(value: str, *, value_kind: str) -> str:
    if value_kind == "url":
        parsed = urlsplit(value)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/..."
        return "configured-url-redacted"
    if len(value) <= 8:
        return "configured-secret-redacted"
    return f"{value[:4]}...{value[-4:]}"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


__all__ = ["REPORT_KIND", "build_external_monitoring_readiness"]
