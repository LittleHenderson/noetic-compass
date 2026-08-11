"""Owner runtime control for external monitoring configuration.

This lets the owner store hosted uptime/error-monitoring and alert hooks from the app
without editing `.env` by hand. The values stay server-side, are masked in all
reports, and do not ping external services on write.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..route_cache import invalidate_cache
from cas_forex.external_monitoring import build_external_monitoring_readiness
from cas_forex.external_monitoring_control import (
    build_external_monitoring_control_report,
    clear_external_monitoring_overrides,
    set_external_monitoring_overrides,
)
from cas_forex.operational_readiness import build_operational_readiness_report
from cas_forex.professional_readiness_matrix import build_professional_readiness_matrix
from cas_forex.public_launch_gate import build_public_launch_gate


router = APIRouter()


class ExternalMonitoringUpdate(BaseModel):
    uptime_monitor_url: Optional[str] = None
    error_tracking_dsn: Optional[str] = None
    alert_webhook_url: Optional[str] = None


def _fresh_reports() -> Dict[str, Any]:
    external = build_external_monitoring_readiness()
    operational = build_operational_readiness_report()
    professional = build_professional_readiness_matrix()
    launch = build_public_launch_gate(
        reports={
            "professional_readiness": professional,
            "operational_readiness": operational,
            "external_monitoring": external,
        }
    )
    return {
        "external_monitoring": external,
        "external_monitoring_control": build_external_monitoring_control_report(),
        "operational_readiness": operational,
        "professional_readiness": professional,
        "public_launch_gate": launch,
    }


def _invalidate_related_caches() -> None:
    invalidate_cache(
        "settings_operational_readiness",
        "settings_professional_readiness",
        "settings_public_launch_gate",
    )


@router.post("/update")
async def update_external_monitoring(body: ExternalMonitoringUpdate) -> Dict[str, Any]:
    provided = {key: getattr(body, key) for key in body.model_fields_set}
    applied_keys = set_external_monitoring_overrides(**provided) if provided else []
    if applied_keys:
        _invalidate_related_caches()
    return {
        "report_kind": "cas_forex_external_monitoring_config_update",
        "status": "UPDATED" if applied_keys else "NO_CHANGES",
        "applied_keys": applied_keys,
        **_fresh_reports(),
        "claim_boundary": (
            "External monitoring config update changes only local runtime hooks "
            "for uptime/error monitoring and alert delivery. It does not ping the configured "
            "services, place orders, move money, or authorize live trading."
        ),
    }


@router.post("/reset")
async def reset_external_monitoring() -> Dict[str, Any]:
    cleared_keys = clear_external_monitoring_overrides()
    if cleared_keys:
        _invalidate_related_caches()
    return {
        "report_kind": "cas_forex_external_monitoring_config_reset",
        "status": "RESET",
        "applied_keys": cleared_keys,
        **_fresh_reports(),
        "claim_boundary": (
            "External monitoring reset clears local runtime overrides only. It "
            "does not remove static env configuration, place orders, move money, "
            "or authorize live trading."
        ),
    }
