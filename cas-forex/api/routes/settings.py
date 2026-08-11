from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from cas_forex.ai_hedge_management_runtime import (
    build_current_ai_hedge_management_handoff,
    build_current_ai_hedge_supervision_report,
)
from cas_forex.backup_restore import create_backup
from cas_forex.bypass_launch_gate import build_bypass_launch_gate_report
from cas_forex.emergency_controls import build_emergency_controls_report
from cas_forex.economic_calendar_feed import build_economic_calendar_feed_report
from cas_forex.legal_review_control import (
    RECORD_CONFIRM_PHRASE,
    LegalReviewControlError,
    build_legal_review_control_report,
    reset_counsel_review_record,
    write_counsel_review_record,
)
from cas_forex.legal_review_readiness import build_legal_review_readiness
from cas_forex.owner_control import clear_owner_control_overrides, set_owner_control_overrides
from cas_forex.operational_readiness import build_operational_readiness_report
from cas_forex.professional_claims import build_professional_claims_report
from cas_forex.professional_readiness_matrix import build_professional_readiness_matrix
from cas_forex.public_launch_gate import build_public_launch_gate
from cas_forex.security_posture import build_security_posture_report
from cas_forex.spec_context import (
    ai_hedge_intelligence_layer,
    autonomous_execution_correction,
    build_status_report as build_spec_context_status_report,
)
from cas_forex.ui_layout_contract import build_ui_layout_contract
from ..route_cache import cache_first_payload, invalidate_cache
from ..data import (
    authority_boundary,
    authority_boundary_fast,
    owner_control,
    runtime_gates_report,
    ai_model_status,
    broker_candidate_profiles,
)

router = APIRouter()
_SETTINGS_CACHE_TTL_SECONDS = 30.0
_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPERATOR_BACKUP_DIR = _REPO_ROOT / "runtime" / "backups"


class OwnerControlUpdate(BaseModel):
    mode: Optional[str] = None
    max_concurrent_trades: Optional[int] = Field(default=None, ge=1)
    max_loss_cap_pct: Optional[float] = Field(default=None, ge=0)
    ai_autonomy_enabled: Optional[bool] = None


class LegalReviewControlUpdate(BaseModel):
    reviewed_by: str = ""
    review_date: str = ""
    scope: str = ""
    review_artifact_path: str = ""
    review_artifact_sha256: str = ""
    matter_reference: str = ""
    jurisdictions: str = ""
    notes: str = ""
    qualified_counsel_confirmed: bool = False
    confirm_phrase: str = ""
    counsel_review_status: str = "accepted"


@router.get("/owner-control")
async def get_owner_control():
    """Returns owner control state."""
    return owner_control()


@router.post("/owner-control/update")
async def post_owner_control(body: OwnerControlUpdate) -> dict[str, Any]:
    """Persist owner-control mode/risk/autonomy overrides for the cockpit."""
    changes = {
        key: getattr(body, key)
        for key in body.model_fields_set
        if getattr(body, key) is not None
    }
    if not changes:
        return owner_control()
    try:
        set_owner_control_overrides(**changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return owner_control()


@router.post("/owner-control/reset")
async def post_owner_control_reset() -> dict[str, Any]:
    """Clear owner-control overrides and return to the default paper policy."""
    clear_owner_control_overrides()
    return owner_control()


@router.get("/authority-boundary")
async def get_authority_boundary():
    """Returns the current owner-controlled live-money authority boundary."""
    return cache_first_payload(
        "settings_authority_boundary",
        builder=authority_boundary,
        fallback=authority_boundary_fast,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/runtime-gates")
async def get_runtime_gates():
    """Returns each real-money capability gate: authorized vs pending owner enable,
    with the exact requirements still missing for each."""
    return cache_first_payload(
        "settings_runtime_gates",
        builder=runtime_gates_report,
        fallback=_runtime_gates_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/ai-model")
async def get_ai_model():
    """Returns the open-weight AI research-model adapter status."""
    return ai_model_status()


@router.get("/broker-candidates")
async def get_broker_candidates():
    """Returns owner-requested broker candidates and verification status."""
    return broker_candidate_profiles()


def _runtime_gates_warming() -> dict[str, Any]:
    capabilities = (
        "live_trading",
        "broker_accept",
        "auto_deposit",
        "bank_card_movement",
        "payout_automation",
    )
    decisions = {
        capability: {
            "capability": capability,
            "authorized": False,
            "status": "CURRENTLY NOT LICENSED",
            "missing_requirements": ["Detailed runtime gate audit is warming."],
            "satisfied_requirements": [],
            "next_action": "Wait for the cached runtime gate report to refresh.",
        }
        for capability in capabilities
    }
    return {
        "report_kind": "cas_forex_runtime_gates",
        "decisions": decisions,
        "all_real_money_authorized": False,
        "summary": "Runtime gates are warming and fail closed as CURRENTLY NOT LICENSED.",
        "claim_boundary": (
            "Warming runtime-gates packet is read-only and fail-closed. It does not "
            "authorize live trading, broker ACCEPT, deposits, withdrawals, bank/card "
            "movement, payouts, or order execution."
        ),
    }


@router.get("/security-posture")
async def get_security_posture():
    """Returns masked security posture for owner auth and local credentials."""
    return cache_first_payload(
        "settings_security_posture",
        builder=build_security_posture_report,
        fallback=_security_posture_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/professional-claims")
async def get_professional_claims():
    """Returns risky-copy and disclosure posture for professional product claims."""
    return cache_first_payload(
        "settings_professional_claims",
        builder=build_professional_claims_report,
        fallback=_professional_claims_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/spec-context")
async def get_spec_context():
    """Returns read-only status for Assistant/Operator spec-sheet context."""
    # This is a small local JSON snapshot, not a broker/dashboard deep build.
    # Keeping it out of the shared cache-refresh queue prevents an unrelated
    # slow MT5 or readiness builder from leaving Operator authority memory at
    # WARMING indefinitely.
    return await run_in_threadpool(build_spec_context_status_report)


@router.get("/ai-hedge-supervision")
async def get_ai_hedge_supervision():
    """Returns read-only AI Hedge runtime supervision recommendations."""
    return cache_first_payload(
        "settings_ai_hedge_supervision",
        builder=build_current_ai_hedge_supervision_report,
        fallback=_ai_hedge_supervision_warming,
        ttl_seconds=10.0,
        block_on_cold=False,
    )


@router.get("/ai-hedge-management-handoff")
async def get_ai_hedge_management_handoff():
    """Returns dry-run AI Hedge broker-management action drafts."""
    return cache_first_payload(
        "settings_ai_hedge_management_handoff",
        builder=build_current_ai_hedge_management_handoff,
        fallback=_ai_hedge_management_handoff_warming,
        ttl_seconds=10.0,
        block_on_cold=False,
    )


@router.get("/legal-review-readiness")
async def get_legal_review_readiness():
    """Returns draft-vs-counsel legal review readiness for public launch."""
    return cache_first_payload(
        "settings_legal_review_readiness",
        builder=build_legal_review_readiness,
        fallback=_legal_review_readiness_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/legal-review-control")
async def get_legal_review_control():
    """Returns the structured owner workflow for the counsel review record."""
    return cache_first_payload(
        "settings_legal_review_control",
        builder=build_legal_review_control_report,
        fallback=_legal_review_control_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


def _invalidate_legal_review_caches() -> None:
    invalidate_cache(
        "settings_legal_review_control",
        "settings_legal_review_readiness",
        "settings_professional_readiness",
        "settings_public_launch_gate",
    )


def _fresh_legal_review_reports() -> dict[str, Any]:
    legal_control = build_legal_review_control_report()
    legal_readiness = build_legal_review_readiness()
    professional = build_professional_readiness_matrix()
    launch = build_public_launch_gate(
        reports={
            "legal_review": legal_readiness,
            "professional_readiness": professional,
        }
    )
    return {
        "legal_review_control": legal_control,
        "legal_review_readiness": legal_readiness,
        "professional_readiness": professional,
        "public_launch_gate": launch,
    }


@router.post("/legal-review-control/update")
async def post_legal_review_control_update(body: LegalReviewControlUpdate) -> dict[str, Any]:
    try:
        control = write_counsel_review_record(
            reviewed_by=body.reviewed_by,
            review_date=body.review_date,
            scope=body.scope,
            review_artifact_path=body.review_artifact_path,
            review_artifact_sha256=body.review_artifact_sha256,
            matter_reference=body.matter_reference,
            jurisdictions=body.jurisdictions,
            notes=body.notes,
            qualified_counsel_confirmed=body.qualified_counsel_confirmed,
            confirm_phrase=body.confirm_phrase,
            counsel_review_status=body.counsel_review_status,
        )
    except LegalReviewControlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _invalidate_legal_review_caches()
    return {
        "report_kind": "cas_forex_legal_review_control_update",
        "status": "UPDATED",
        "required_confirm_phrase": RECORD_CONFIRM_PHRASE,
        "legal_review_control": control,
        **_fresh_legal_review_reports(),
        "claim_boundary": (
            "Legal review control update writes metadata about an external "
            "qualified counsel review record. It does not provide legal advice, "
            "self-certify launch approval, place orders, move money, or "
            "authorize live trading."
        ),
    }


@router.post("/legal-review-control/reset")
async def post_legal_review_control_reset() -> dict[str, Any]:
    control = reset_counsel_review_record()
    _invalidate_legal_review_caches()
    return {
        "report_kind": "cas_forex_legal_review_control_reset",
        "status": "RESET",
        "required_confirm_phrase": RECORD_CONFIRM_PHRASE,
        "legal_review_control": control,
        **_fresh_legal_review_reports(),
        "claim_boundary": (
            "Legal review control reset removes the local counsel review record "
            "metadata only. It does not provide legal advice, place orders, move "
            "money, or authorize live trading."
        ),
    }


@router.get("/professional-readiness")
async def get_professional_readiness():
    """Returns the 37-item professional trading-app readiness matrix."""
    return cache_first_payload(
        "settings_professional_readiness",
        builder=build_professional_readiness_matrix,
        fallback=_professional_readiness_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/public-launch-gate")
async def get_public_launch_gate():
    """Returns the aggregate public/live-production launch gate."""
    return cache_first_payload(
        "settings_public_launch_gate",
        builder=build_public_launch_gate,
        fallback=_public_launch_gate_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/bypass-launch-gate")
async def get_bypass_launch_gate():
    """Returns static no-bypass launch-gate evidence for sensitive paths."""
    return cache_first_payload(
        "settings_bypass_launch_gate",
        builder=build_bypass_launch_gate_report,
        fallback=_bypass_launch_gate_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/ui-layout-contract")
async def get_ui_layout_contract():
    """Returns static UI layout/zoom contract checks for the cockpit."""
    return cache_first_payload(
        "settings_ui_layout_contract",
        builder=build_ui_layout_contract,
        fallback=_ui_layout_contract_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/economic-calendar")
async def get_economic_calendar():
    """Returns configured external economic-calendar feed/cache status."""
    return cache_first_payload(
        "settings_economic_calendar",
        builder=build_economic_calendar_feed_report,
        fallback=_economic_calendar_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/operational-readiness")
async def get_operational_readiness():
    """Returns production-operations readiness evidence for local CAS Forex."""
    return cache_first_payload(
        "settings_operational_readiness",
        builder=build_operational_readiness_report,
        fallback=_operational_readiness_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.get("/emergency-controls")
async def get_emergency_controls():
    """Returns emergency-control coverage and broker-exposure gaps."""
    return cache_first_payload(
        "settings_emergency_controls",
        builder=build_emergency_controls_report,
        fallback=_emergency_controls_warming,
        ttl_seconds=_SETTINGS_CACHE_TTL_SECONDS,
        block_on_cold=False,
    )


@router.post("/operator-backup/create")
async def post_operator_backup_create() -> dict[str, Any]:
    """Create a local operator-state backup snapshot."""
    manifest = create_backup(repo_root=_REPO_ROOT, snapshot_dir=_OPERATOR_BACKUP_DIR)
    payload = asdict(manifest)
    created = bool(payload.get("snapshot_path"))
    return {
        "report_kind": "cas_forex_operator_backup_create",
        "status": "CREATED" if created else "FAILED_OR_EMPTY",
        "manifest": payload,
        "operational_readiness": build_operational_readiness_report(),
        "snapshot_dir": str(_OPERATOR_BACKUP_DIR),
        "claim_boundary": (
            "Operator backup creation writes a local ZIP snapshot of selected "
            "operator-critical state. It does not restore files, restart "
            "processes, place orders, close positions, move money, or authorize "
            "live trading."
        ),
    }


def _security_posture_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_security_posture",
        "status": "WARMING",
        "attention_items": ["Security posture cache is warming."],
        "owner_auth": {"owner_token_present": False, "lan_mode_enabled": False},
        "browser_exposure": {"browser_storage_keys": []},
        "managed_secret_store": {
            "report_kind": "cas_forex_managed_secret_store",
            "status": "WARMING",
            "backend_status": "UNKNOWN",
            "active_backend": "",
            "requested_backend": "auto",
            "cloud_mode": False,
            "external_secret_manager": {"configured": False, "provider": "", "provider_set": False},
            "os_current_user_store": {},
            "windows_credential_manager": {},
            "runtime_secret_envelope": {},
            "server_side_only": True,
            "raw_secret_returned": False,
            "attention_items": [],
            "detail": "Managed secret-store posture is warming.",
            "claim_boundary": "Managed secret-store cache warming is read-only and returns no raw secrets.",
        },
        "server_secret_inventory": [],
        "ignore_coverage": {},
        "permission_surface": {},
        "role_permission_model": {
            "report_kind": "cas_forex_role_permission_model",
            "status": "WARMING",
            "authorization_model": "single_owner_local_app_with_owner_token_for_off_box_access",
            "mfa_status": "UNKNOWN",
            "mfa_detail": "Security posture cache is warming.",
            "roles": [],
            "route_permission_policy": {
                "report_kind": "cas_forex_route_permission_policy",
                "status": "WARMING",
                "authorization_model": "owner_auth_admission_plus_route_permission_policy",
                "permission_count": 0,
                "role_count": 0,
                "route_rule_count": 0,
                "money_or_live_sensitive_rule_count": 0,
                "loopback_only_rule_count": 0,
                "permissions": [],
                "roles": [],
                "route_rules": [],
                "default_rules": [],
                "claim_boundary": "Route permission policy cache warming is read-only.",
            },
            "gaps": [],
            "claim_boundary": "Role permission model cache warming is read-only.",
        },
        "claim_boundary": (
            "Security posture cache warming is read-only and returns no raw "
            "tokens, passwords, broker credentials, payment keys, or model keys."
        ),
    }


def _operational_readiness_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_operational_readiness",
        "status": "WARMING",
        "ok_count": 0,
        "attention_count": 0,
        "checks": [],
        "attention_items": ["Operational readiness cache is warming."],
        "top_attention_items": ["Operational readiness cache is warming."],
        "next_action": "Wait for operational readiness to refresh.",
        "backup_inventory": {
            "snapshot_count": 0,
            "latest_snapshot": None,
            "snapshot_dirs": [],
            "snapshots": [],
        },
        "external_monitoring": {
            "report_kind": "cas_forex_external_monitoring_readiness",
            "status": "WARMING",
            "ok_count": 0,
            "attention_count": 0,
            "checks": [],
            "health_endpoints": [],
            "required_env": {},
            "top_attention_items": ["External monitoring readiness cache is warming."],
            "next_action": "Wait for external monitoring readiness to refresh.",
            "claim_boundary": (
                "External monitoring cache warming is read-only and does not "
                "ping external services, send alerts, place orders, close "
                "positions, move money, or authorize live trading."
            ),
        },
        "runbook_path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
        "claim_boundary": (
            "Operational readiness cache warming is read-only. It does not "
            "restart processes, restore backups, place orders, close positions, "
            "move money, or authorize live trading."
        ),
    }


def _professional_readiness_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_professional_readiness_matrix",
        "status": "WARMING",
        "item_count": 0,
        "ok_count": 0,
        "partial_count": 0,
        "gap_count": 0,
        "satisfied_count": 0,
        "internal_partial_count": 0,
        "external_blocked_count": 0,
        "missing_count": 0,
        "rows": [],
        "top_attention_items": ["Professional readiness matrix cache is warming."],
        "claim_boundary": (
            "Professional readiness matrix cache warming is read-only. It does "
            "not place orders, close positions, move money, change settings, "
            "authorize live trading, provide legal advice, or promise returns."
        ),
    }


def _spec_context_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_spec_context_status",
        "status": "WARMING",
        "available": False,
        "source_found": False,
        "source": None,
        "snapshot_stale": False,
        "assistant_prompt_available": False,
        "operator_prompt_available": False,
        "ai_hedge_intelligence_layer": ai_hedge_intelligence_layer(),
        "autonomous_execution_correction": autonomous_execution_correction(),
        "assistant_context_chars": 0,
        "operator_constitution_chars": 0,
        "sheet_count": 0,
        "json_path": "runtime/spec_context/spec_context.json",
        "markdown_path": "runtime/spec_context/spec_context.md",
        "operator_constitution_path": "runtime/spec_context/operator_constitution.md",
        "refresh_command": "python scripts/refresh_spec_context.py",
        "surfaces": {},
        "next_action": "Wait for the spec context status report to refresh.",
        "claim_boundary": (
            "Spec context cache warming exposes product authority memory. Actual "
            "trade or money-movement side effects still require backend dispatch/"
            "provider gates, broker/provider truth, risk caps, receipts, and "
            "kill-switch checks."
        ),
    }


def _ai_hedge_supervision_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_ai_hedge_supervision",
        "status": "WARMING",
        "layer_status": "SPECIFIED_GOVERNED_LAYER",
        "thesis": (
            "CAS treats the AI Operator as the adaptive trading edge engine: it "
            "seeks evidence-backed opportunity, selects or stands down strategies, "
            "supervises exits, and hedges rigid strategy behavior plus human "
            "trading psychology inside deterministic guardrails."
        ),
        "movement_stream_id": "WARMING",
        "movement_timestamp": "",
        "price_source_status": "CACHE_WARMING",
        "price_source_label": "WARMING",
        "price_source_summary": "AI Hedge supervision is waiting for movement-stream source truth.",
        "price_source_warning": None,
        "position_feed_label": "WARMING",
        "position_feed_detail": "AI Hedge supervision is waiting for canonical movement position-feed truth.",
        "static_simulation_active": False,
        "provider_usable_symbols": [],
        "static_fallback_symbols": [],
        "position_count": 0,
        "recommendation_count": 0,
        "action_recommendation_count": 0,
        "high_urgency_count": 0,
        "source_health": {
            "price_source_status": "CACHE_WARMING",
            "fresh_for_trade_management": False,
            "static_simulation_active": False,
            "provider_usable_symbol_count": 0,
            "static_fallback_symbol_count": 0,
            "position_feed_label": "WARMING",
            "position_feed_detail": "AI Hedge supervision is waiting for canonical movement position-feed truth.",
            "detail": "AI Hedge supervision is waiting for canonical movement position-feed truth.",
            "summary": "AI Hedge supervision is waiting for movement-stream source truth.",
            "warning": None,
        },
        "positions": [],
        "recommendations": [],
        "allowed_trade_intents": [
            "enter",
            "skip",
            "reduce",
            "close_partial",
            "close_full",
            "trail_stop",
            "move_stop_to_breakeven",
            "pause_strategy",
            "switch_strategy",
            "stand_down",
        ],
        "hard_boundaries": [
            "All broker-bound intent must pass through order_dispatch.py.",
            "execution_guard.py remains the final pre-broker gate.",
            "Live-capable entries require fresh one-use edge PASS authorization.",
            "Fresh broker truth is required before live dispatch.",
        ],
        "broker_bound_action_authorized": False,
        "orders_placed": False,
        "money_moved": False,
        "execution_required_path": [
            "order_dispatch.py",
            "execution_guard.py",
            "edge PASS",
            "broker truth",
            "risk gates",
            "mode separation",
            "owner controls",
        ],
        "next_action": "Wait for the AI Hedge supervision report to refresh.",
        "claim_boundary": (
            "AI Hedge supervision cache warming is the observation stage. Once "
            "fresh, its intents feed the autonomous management executor, where "
            "execution_guard.py, broker truth, owner authority, and receipts apply."
        ),
    }


def _ai_hedge_management_handoff_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_ai_hedge_management_handoff",
        "status": "WARMING",
        "supervision_status": "WARMING",
        "movement_stream_id": "WARMING",
        "movement_timestamp": "",
        "price_source_status": "CACHE_WARMING",
        "price_source_label": "WARMING",
        "static_simulation_active": False,
        "source_health": {
            "price_source_status": "CACHE_WARMING",
            "fresh_for_trade_management": False,
            "summary": "AI Hedge management handoff is waiting for supervision and movement-stream source truth.",
        },
        "position_count": 0,
        "recommendation_count": 0,
        "actionable_recommendation_count": 0,
        "management_action_count": 0,
        "blocked_action_count": 0,
        "skipped_recommendation_count": 0,
        "ready_for_owner_review": False,
        "ready_for_guarded_execution": False,
        "dry_run_only": False,
        "broker_bound_action_authorized": False,
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "management_actions": [],
        "blocked_actions": [],
        "skipped_recommendations": [],
        "execution_required_path": [
            "AI Hedge management handoff",
            "guarded execution",
            "fresh broker truth refresh",
            "execution_guard.py management review",
            "broker bridge modify_position or close_position",
            "terminal receipt and audit reconciliation",
        ],
        "next_action": "Wait for AI Hedge management handoff to refresh.",
        "claim_boundary": (
            "AI Hedge management handoff cache warming prepares guarded execution "
            "drafts. It does not call broker bridges by itself or bypass execution guards."
        ),
    }


def _legal_review_control_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_legal_review_control",
        "status": "WARMING",
        "record_path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        "audit_path": "runtime/legal-review-record-audit.jsonl",
        "required_confirm_phrase": RECORD_CONFIRM_PHRASE,
        "file_present": False,
        "current_record": {
            "file_present": False,
            "counsel_review_status": "",
            "reviewed_by": "",
            "review_date": "",
            "scope": "",
            "qualified_counsel_confirmed": False,
            "review_artifact_path": "",
            "review_artifact_sha256": "",
            "matter_reference": "",
            "jurisdictions": "",
            "notes": "",
            "recorded_via": "",
            "recorded_at": "",
            "artifact_path_exists_locally": False,
            "artifact_hash_looks_valid": False,
        },
        "claim_boundary": (
            "Legal review control warming is read-only. It does not provide legal "
            "advice, create launch approval, authorize live trading, place orders, "
            "or move money."
        ),
    }


def _legal_review_readiness_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_legal_review_readiness",
        "status": "WARMING",
        "launch_legal_status": "WARMING",
        "counsel_review_accepted": False,
        "ok_count": 0,
        "attention_count": 0,
        "checks": [],
        "required_documents": {
            "drafts": [
                "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md",
                "docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md",
                "docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md",
            ],
            "checklist": "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md",
            "counsel_review_record": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        },
        "counsel_review_record_path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        "top_attention_items": ["Legal review readiness cache is warming."],
        "next_action": (
            "Wait for the legal review readiness report to refresh; draft docs "
            "must not be treated as counsel-approved public-launch approval."
        ),
        "claim_boundary": (
            "Legal review readiness cache warming is read-only. It does not "
            "provide legal advice, approve public launch, authorize live "
            "trading, place orders, close positions, move money, or promise "
            "returns."
        ),
    }


def _public_launch_gate_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_public_launch_gate",
        "status": "WARMING",
        "launch_gate_status": "WARMING",
        "public_launch_status": "WARMING",
        "live_money_production_status": "WARMING",
        "gate_count": 0,
        "pass_count": 0,
        "block_count": 0,
        "hard_blocker_count": 0,
        "gates": [],
        "hard_blockers": ["Public launch gate cache is warming."],
        "source_reports": {},
        "release_policy": (
            "Treat WARMING as not ready for public, hosted, paid, multi-user, "
            "or live-money production use until the aggregate gate refreshes."
        ),
        "next_action": "Wait for the public launch gate report to refresh.",
        "claim_boundary": (
            "Public launch gate cache warming is read-only. It does not "
            "provide legal advice, approve public launch, authorize live "
            "trading, place orders, close positions, move money, change "
            "settings, expose secrets, or promise returns."
        ),
    }


def _bypass_launch_gate_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_bypass_launch_gate",
        "status": "WARMING",
        "launch_gate_status": "WARMING",
        "check_count": 0,
        "ok_count": 0,
        "attention_count": 0,
        "checks": [],
        "top_attention_items": ["Bypass launch gate cache is warming."],
        "release_policy": (
            "Treat ATTENTION as a release blocker for any real-money or public "
            "launch path until no-bypass evidence refreshes."
        ),
        "claim_boundary": (
            "Bypass launch gate cache warming is read-only. It does not run "
            "pytest, place orders, close positions, move money, change settings, "
            "or authorize live trading."
        ),
    }


def _emergency_controls_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_emergency_controls",
        "status": "WARMING",
        "ok_count": 0,
        "attention_count": 0,
        "automation_stop_ok": False,
        "broker_exposure_gap": True,
        "controls": [],
        "attention_items": ["Emergency controls coverage cache is warming."],
        "automation_stop_scope": (
            "Emergency controls coverage is warming; verify dashboard emergency "
            "stop and broker terminal access before relying on the app state."
        ),
        "recommended_terminal_actions": [
            "Keep MT4/MT5 visible when automation is running.",
            "Use broker terminal controls for urgent existing-position management until the coverage report refreshes.",
        ],
        "claim_boundary": (
            "Emergency controls cache warming is read-only. It does not start "
            "or stop processes, place orders, close positions, cancel orders, "
            "move money, clear auto-halt, or authorize live trading."
        ),
    }


def _ui_layout_contract_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_ui_layout_zoom_contract",
        "status": "WARMING",
        "ok_count": 0,
        "attention_count": 0,
        "check_count": 0,
        "checks": [],
        "route_count": 0,
        "missing_page_routes": [],
        "css_zoom_violations": [],
        "top_attention_items": ["UI layout contract cache is warming."],
        "claim_boundary": (
            "UI layout contract cache warming is read-only. It does not render "
            "pages, place orders, close positions, move money, change settings, "
            "authorize live trading, or promise returns."
        ),
    }


def _economic_calendar_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_economic_calendar_feed",
        "status": "WARMING",
        "source_status": "UNKNOWN",
        "configured": False,
        "checked_at_iso": None,
        "source_kind": "unknown",
        "source": "",
        "source_is_http": False,
        "cache_path": "",
        "cache_ttl_seconds": 0,
        "cache_written_at_epoch": None,
        "cache_age_seconds": None,
        "cache_stale": False,
        "fail_closed_on_error": False,
        "event_count": 0,
        "raw_event_count": 0,
        "unusable_event_count": 0,
        "events": [],
        "detail": "Economic-calendar feed status is warming.",
        "error": None,
        "claim_boundary": (
            "Economic calendar cache warming is read-only. It does not place "
            "orders, close positions, move money, change settings, authorize "
            "live trading, or promise returns."
        ),
    }


def _professional_claims_warming() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_professional_claims",
        "status": "WARMING",
        "risky_claim_count": 0,
        "boundary_reference_count": 0,
        "claim_hits": [],
        "disclosure_document": {
            "path": "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md",
            "present": False,
            "line_count": 0,
            "summary": "Professional claims cache is warming.",
        },
        "required_disclosures": [],
        "missing_disclosures": [],
        "copy_policy": {
            "forbidden_claim_types": [],
            "preferred_language": [],
        },
        "claim_boundary": (
            "Professional claims cache warming is read-only. It does not "
            "authorize trading, block trading, provide legal advice, or "
            "promise returns."
        ),
    }
