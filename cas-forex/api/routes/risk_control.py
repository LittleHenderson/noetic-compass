"""HTTP routes for owner risk control: set any concurrent-trade count / loss cap.

``GET /state`` reports the owner-editing layer, durable override status, and the
separately resolved effective dispatch caps; ``POST /preview`` explains the exact
before/after impact of a pending change; ``POST /preview-reset`` previews what a
reset would do; ``POST /update`` sets caps (a number = a cap, ``null`` =
UNLIMITED / remove the cap); ``POST /reset`` reverts to config defaults.
Only fields actually present in the request body are changed.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cas_forex.risk_control import (
    RISK_LOOSEN_CONFIRM_PHRASE,
    assess_risk_control_reset,
    assess_risk_control_update,
    build_risk_control_audit_report,
    build_risk_control_report,
    clear_risk_control_overrides,
    set_risk_control_overrides,
)

router = APIRouter()


class RiskControlUpdate(BaseModel):
    # number = cap on that dimension; null = unlimited (no cap). Omit = leave as-is.
    max_concurrent_trades: Optional[int] = Field(default=None, ge=0)
    max_total_exposure_lots: Optional[float] = Field(default=None, ge=0)
    max_loss_cap_usd: Optional[float] = Field(default=None, ge=0)
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0)
    # Required only when this request loosens/removes a cap while real-money
    # controls are armed. Tightening caps never needs this.
    confirm: Optional[str] = None
    # Required whenever this request loosens/removes a cap. This is separate
    # from confirm because it records the anti-impulse rationale.
    journal_reason: Optional[str] = None


class RiskControlResetRequest(BaseModel):
    confirm: Optional[str] = None
    journal_reason: Optional[str] = None


def _norm_confirm(text: Any) -> str:
    return " ".join(str(text or "").strip().upper().split())


@router.get("/state")
async def get_risk_control() -> dict[str, Any]:
    """Durable owner overrides plus the actual resolved dispatch caps."""
    return build_risk_control_report()


@router.get("/audit")
async def get_risk_control_audit(limit: int = 25) -> dict[str, Any]:
    """Recent append-only risk-control changes, newest first."""
    return build_risk_control_audit_report(limit)


@router.post("/preview")
async def preview_risk_control(body: RiskControlUpdate) -> dict[str, Any]:
    """Preview cap changes without applying them."""
    provided = {
        key: getattr(body, key)
        for key in body.model_fields_set
        if key not in {"confirm", "journal_reason"}
    }
    if not provided:
        return assess_risk_control_update({})
    return assess_risk_control_update(provided, journal_reason=body.journal_reason or "")


@router.post("/preview-reset")
async def preview_reset_risk_control(body: RiskControlResetRequest | None = None) -> dict[str, Any]:
    """Preview what resetting all overrides back to config defaults would do."""
    body = body or RiskControlResetRequest()
    return assess_risk_control_reset(journal_reason=body.journal_reason or "")


@router.post("/update")
async def post_risk_control(body: RiskControlUpdate) -> dict[str, Any]:
    """Set caps. Field present with a number = cap; present with null = unlimited;
    omitted = unchanged."""
    provided = {
        key: getattr(body, key)
        for key in body.model_fields_set
        if key not in {"confirm", "journal_reason"}
    }
    if not provided:
        return build_risk_control_report()
    assessment = assess_risk_control_update(provided, journal_reason=body.journal_reason or "")
    journal = assessment.get("journal") if isinstance(assessment.get("journal"), dict) else {}
    if assessment.get("requires_journal_reason") and not journal.get("satisfied"):
        raise HTTPException(status_code=409, detail={
            "status": "JOURNAL_REQUIRED",
            "assessment": assessment,
            "journal": journal,
        })
    if assessment["requires_confirmation"] and _norm_confirm(body.confirm) != RISK_LOOSEN_CONFIRM_PHRASE:
        raise HTTPException(status_code=409, detail={
            "status": "CONFIRM_REQUIRED",
            "need_confirmation": RISK_LOOSEN_CONFIRM_PHRASE,
            "assessment": assessment,
        })
    if assessment.get("requires_cooldown_clear"):
        raise HTTPException(status_code=409, detail={
            "status": "COOLDOWN_ACTIVE",
            "assessment": assessment,
            "cooldown": assessment.get("cooldown"),
        })
    try:
        set_risk_control_overrides(
            **provided,
            audit_source="api.risk_control.update",
            audit_confirm_supplied=bool(body.confirm),
            audit_assessment=assessment,
            audit_journal_reason=body.journal_reason or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail={
            "status": "RISK_OVERRIDE_PERSISTENCE_FAILED",
            "detail": f"{type(exc).__name__}: {exc}",
            "money_impact": "No new owner risk override became active.",
        }) from exc
    report = build_risk_control_report()
    report["last_update_assessment"] = assessment
    return report


@router.post("/reset")
async def post_reset_risk_control(body: RiskControlResetRequest | None = None) -> dict[str, Any]:
    """Clear all overrides (revert to config defaults)."""
    body = body or RiskControlResetRequest()
    assessment = assess_risk_control_reset(journal_reason=body.journal_reason or "")
    journal = assessment.get("journal") if isinstance(assessment.get("journal"), dict) else {}
    if assessment.get("requires_journal_reason") and not journal.get("satisfied"):
        raise HTTPException(status_code=409, detail={
            "status": "JOURNAL_REQUIRED",
            "assessment": assessment,
            "journal": journal,
        })
    if assessment["requires_confirmation"] and _norm_confirm(body.confirm) != RISK_LOOSEN_CONFIRM_PHRASE:
        raise HTTPException(status_code=409, detail={
            "status": "CONFIRM_REQUIRED",
            "need_confirmation": RISK_LOOSEN_CONFIRM_PHRASE,
            "assessment": assessment,
        })
    if assessment.get("requires_cooldown_clear"):
        raise HTTPException(status_code=409, detail={
            "status": "COOLDOWN_ACTIVE",
            "assessment": assessment,
            "cooldown": assessment.get("cooldown"),
        })
    try:
        clear_risk_control_overrides(
            audit_source="api.risk_control.reset",
            audit_confirm_supplied=bool(body.confirm),
            audit_assessment=assessment,
            audit_journal_reason=body.journal_reason or "",
        )
    except OSError as exc:
        raise HTTPException(status_code=503, detail={
            "status": "RISK_OVERRIDE_PERSISTENCE_FAILED",
            "detail": f"{type(exc).__name__}: {exc}",
            "money_impact": "Existing owner risk overrides remain active.",
        }) from exc
    return build_risk_control_report()
