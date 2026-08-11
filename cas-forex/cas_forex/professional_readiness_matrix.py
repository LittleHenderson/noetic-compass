"""Read-only professional engineering readiness matrix for CAS Forex.

This report maps the common "vibe-coded trading app" failure modes to concrete
CAS Forex evidence. It is intentionally diagnostic: it helps the owner see what
is built, what is partial, and what remains a production gap without changing
any trading, broker, or money state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from cas_forex.legal_review_readiness import build_legal_review_readiness
from cas_forex.operational_readiness import build_operational_readiness_report


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_professional_readiness_matrix"

CLAIM_BOUNDARY = (
    "Professional readiness matrix is a read-only product/engineering audit. "
    "It reports evidence and remaining gaps against professional trading-app "
    "standards. It does not place orders, close positions, move money, change "
    "risk settings, authorize live trading, provide legal advice, or promise "
    "returns."
)


def build_professional_readiness_matrix(
    root: Path | str | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    rows = [_row(base=base, **item) for item in _MATRIX_ITEMS]
    rows = _apply_dynamic_status_overrides(base, rows, env=env)
    ok_count = sum(1 for row in rows if row["status"] == "OK")
    partial_count = sum(1 for row in rows if row["status"] == "PARTIAL")
    gap_count = sum(1 for row in rows if row["status"] == "GAP")
    external_blocked_count = sum(
        1 for row in rows if bool(row.get("blocked_by_external_dependency"))
    )
    satisfied_count = sum(1 for row in rows if row["completion_state"] == "SATISFIED")
    internal_partial_count = sum(1 for row in rows if row["completion_state"] == "PARTIAL")
    missing_count = sum(1 for row in rows if row["completion_state"] == "MISSING")
    attention_count = partial_count + gap_count
    return {
        "report_kind": REPORT_KIND,
        "status": "OK" if attention_count == 0 else "ATTENTION",
        "item_count": len(rows),
        "ok_count": ok_count,
        "partial_count": partial_count,
        "gap_count": gap_count,
        "satisfied_count": satisfied_count,
        "internal_partial_count": internal_partial_count,
        "external_blocked_count": external_blocked_count,
        "missing_count": missing_count,
        "attention_count": attention_count,
        "rows": rows,
        "top_attention_items": _unique_nonempty(
            row["next_action"]
            for row in rows
            if row["status"] in {"GAP", "PARTIAL"}
        )[:8],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _apply_dynamic_status_overrides(
    base: Path,
    rows: list[dict[str, Any]],
    *,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    legal_review = build_legal_review_readiness(base)
    operational_readiness = build_operational_readiness_report(base, env=env)
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["key"] in {"compliance_awareness", "legal_disclosures"}:
            out.append(_apply_legal_review_row(row, legal_review))
            continue
        if row["key"] == "production_operations":
            out.append(_apply_operational_row(row, operational_readiness))
            continue
        out.append(row)
    return out


def _apply_legal_review_row(row: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    if bool(report.get("counsel_review_accepted")) and report.get("status") == "OK":
        return _override_row_state(row, status="OK")
    row_key = str(row.get("key") or "")
    next_action = (
        str(row.get("next_action") or "")
        if row_key == "legal_disclosures"
        else str(report.get("next_action") or "")
    )
    return _override_row_state(
        row,
        status="PARTIAL",
        remaining_gap=str(
            row.get("remaining_gap")
            or "Counsel-reviewed public-launch legal record is still missing."
        ),
        partial_terms=("counsel_review",),
        next_action=next_action
        or str(row.get("next_action") or "")
        or str(report.get("next_action") or "")
        or "Complete qualified legal/compliance review before public launch.",
    )


def _apply_operational_row(row: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    external = report.get("external_monitoring") if isinstance(report.get("external_monitoring"), Mapping) else {}
    if report.get("status") == "OK" and external.get("status") == "OK":
        return _override_row_state(row, status="OK")

    checks = external.get("checks") if isinstance(external.get("checks"), list) else []
    check_by_key = {
        str(item.get("key")): item
        for item in checks
        if isinstance(item, Mapping) and item.get("key")
    }
    partial_terms: list[str] = []
    if str((check_by_key.get("external_uptime_monitor") or {}).get("status")) != "OK":
        partial_terms.append("external_uptime_monitoring_configured")
    if str((check_by_key.get("error_tracking_dsn") or {}).get("status")) != "OK":
        partial_terms.append("error_tracking_dsn_configured")
    remaining_gap = (
        str((external.get("top_attention_items") or [None])[0] or "")
        or str((report.get("attention_items") or [None])[0] or "")
        or str(row.get("remaining_gap") or "")
    )
    return _override_row_state(
        row,
        status="PARTIAL",
        remaining_gap=remaining_gap,
        partial_terms=tuple(partial_terms or row.get("partial_terms") or ()),
        next_action=str(
            external.get("next_action")
            or row.get("next_action")
            or "Add external uptime/error monitoring before public cloud deployment."
        ),
    )


def _override_row_state(
    row: Mapping[str, Any],
    *,
    status: str,
    remaining_gap: str = "",
    partial_terms: Iterable[str] = (),
    next_action: str = "",
) -> dict[str, Any]:
    out = dict(row)
    out["status"] = status
    if status == "OK":
        out["remaining_gap"] = ""
        out["partial_terms"] = []
        out["external_dependency"] = ""
        out["blocked_by_external_dependency"] = False
        out["blocker_type"] = "none"
        out["completion_state"] = "SATISFIED"
        out["next_action"] = "Keep this coverage regression-tested."
        return out
    out["remaining_gap"] = str(remaining_gap or row.get("remaining_gap") or "")
    out["partial_terms"] = [str(term) for term in partial_terms if str(term)]
    out["next_action"] = str(next_action or row.get("next_action") or "")
    _attach_completion_state(out)
    return out


def _row(
    *,
    base: Path,
    item_number: int,
    key: str,
    category: str,
    standard: str,
    evidence: Iterable[str],
    gap: str,
    next_action: str,
    partial_terms: Iterable[str] = (),
    external_dependency: str = "",
) -> dict[str, Any]:
    evidence_refs = list(evidence)
    present_refs = [ref for ref in evidence_refs if _evidence_present(base, ref)]
    missing_refs = [ref for ref in evidence_refs if ref not in present_refs]
    terms = [term for term in partial_terms if term]
    if not evidence_refs:
        status = "GAP"
    elif missing_refs:
        status = "PARTIAL" if present_refs else "GAP"
    elif terms:
        status = "PARTIAL"
    else:
        status = "OK"
    row = {
        "item_number": item_number,
        "key": key,
        "category": category,
        "status": status,
        "professional_standard": standard,
        "evidence_refs": evidence_refs,
        "present_evidence_refs": present_refs,
        "missing_evidence_refs": missing_refs,
        "remaining_gap": gap if status != "OK" else "",
        "partial_terms": terms,
        "external_dependency": external_dependency if status != "OK" else "",
        "next_action": next_action if status != "OK" else "Keep this coverage regression-tested.",
    }
    _attach_completion_state(row)
    return row


def _attach_completion_state(row: dict[str, Any]) -> None:
    status = str(row.get("status") or "").upper()
    external_dependency = str(row.get("external_dependency") or "").strip()
    blocked_by_external = bool(external_dependency and status != "OK")
    row["blocked_by_external_dependency"] = blocked_by_external
    row["blocker_type"] = "external" if blocked_by_external else ("none" if status == "OK" else "code")
    if status == "OK":
        row["completion_state"] = "SATISFIED"
    elif status == "GAP":
        row["completion_state"] = "MISSING"
    elif blocked_by_external:
        row["completion_state"] = "EXTERNAL_BLOCKED"
    else:
        row["completion_state"] = "PARTIAL"


def _evidence_present(base: Path, ref: str) -> bool:
    path_text, markers = _split_evidence_ref(ref)
    if path_text.startswith("/api/"):
        return True
    path = base / path_text
    if any(char in path_text for char in "*?[]"):
        matches = list(base.glob(path_text))
        if not matches or markers:
            return bool(matches) and not markers
        return True
    if not path.exists():
        return False
    if not markers:
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return all(marker in text for marker in markers)


def _split_evidence_ref(ref: str) -> tuple[str, list[str]]:
    path_text = ref
    marker_text = ""
    if ref.startswith("route:") or ref.startswith("ui:") or ref.startswith("test:"):
        path_text = ref.split(":", 1)[1]
    if not path_text.startswith("/api/") and ":" in path_text:
        path_text, marker_text = path_text.split(":", 1)
    markers = [part.strip() for part in marker_text.split() if part.strip()]
    return path_text, markers


def _unique_nonempty(values: Iterable[Any]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


_MATRIX_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "item_number": 1,
        "key": "hard_risk_engine",
        "category": "Risk Engine",
        "standard": "AI proposals must be approved by deterministic server-side risk gates before broker dispatch.",
        "evidence": ("cas_forex/pre_execution_risk_gate.py", "cas_forex/order_dispatch.py", "tests/test_pre_execution_risk_gate.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 2,
        "key": "cas_dial_definitions",
        "category": "Control Dials",
        "standard": "Every CAS dial maps to concrete bounded parameters, owner limits, effects, and audit rows.",
        "evidence": ("cas_forex/ai_control_authority.py", "tests/test_ai_control_authority.py", "ui/src/pages/SettingsPage.tsx"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 3,
        "key": "live_mode_ceremony",
        "category": "Live Authority",
        "standard": "Autonomy is staged from lockdown/signal/paper to live-confirmed operation with explicit owner ceremony.",
        "evidence": ("cas_forex/owner_control.py", "cas_forex/runtime_gates.py", "tests/test_runtime_gates.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 4,
        "key": "duplicate_order_protection",
        "category": "Execution Safety",
        "standard": "Retries, reconnects, and duplicate intents must be idempotent before the broker bridge is touched.",
        "evidence": ("cas_forex/order_attempt_audit.py", "cas_forex/order_dispatch.py", "tests/test_order_dispatch.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 5,
        "key": "mt4_mt5_adapter_separation",
        "category": "Broker Adapters",
        "standard": "MT4 and MT5 paths must be explicit adapters with separate permissions, receipts, and failure handling.",
        "evidence": ("cas_forex/broker/mt5_bridge.py", "api/routes/mt4_control.py", "cas_forex/mt4_terminal_session_verifier.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 6,
        "key": "broker_state_reconciliation",
        "category": "Broker Truth",
        "standard": "Broker/terminal truth is the source of record for balance, positions, pending orders, and recovery.",
        "evidence": (
            "cas_forex/broker_truth_monitor.py",
            "cas_forex/account_reconciliation.py",
            "cas_forex/terminal_position_reconciliation.py",
            "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 7,
        "key": "trade_explanation_cards",
        "category": "Explainability",
        "standard": "Every opened, blocked, or rejected trade needs a human-readable reason, gate trace, audit id, and money impact.",
        "evidence": ("cas_forex/order_dispatch.py", "cas_forex/agent_decision_explainer.py", "ui/src/components/AgentDecisionCard.tsx"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 8,
        "key": "fake_precision_control",
        "category": "AI Claims",
        "standard": "AI confidence must not be presented as a fake win probability; conviction language and caveats are required.",
        "evidence": ("cas_forex/agent_state.py", "cas_forex/ai_operator.py", "tests/test_agent_message_bus.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 9,
        "key": "backtest_discipline",
        "category": "Performance",
        "standard": "Backtest/performance screens must include costs, drawdown, sample size, out-of-sample, Monte Carlo, and mode separation.",
        "evidence": ("cas_forex/performance_discipline.py", "ui/src/pages/StrategyComparisonPage.tsx", "tests/test_performance_discipline.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 10,
        "key": "paper_first_progression",
        "category": "Live Authority",
        "standard": "Live progression requires paper/demo evidence, live dry-run review, and small controlled pilot capacity.",
        "evidence": ("cas_forex/live_order_dry_run_review.py", "cas_forex/live_pilot.py", "cas_forex/live_readiness.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 11,
        "key": "anti_impulse_controls",
        "category": "Trading Psychology",
        "standard": "The app must prevent emotional parameter chasing with cooldowns, anti-loosening visibility, and audit evidence.",
        "evidence": (
            "cas_forex/ai_control_authority.py:anti_impulse_journal",
            "cas_forex/risk_control.py",
            "api/routes/order_dispatch.py:manual_order_journal",
            "ui/src/pages/SettingsPage.tsx",
            "tests/test_ai_control_authority.py",
            "tests/test_order_dispatch_route.py",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 12,
        "key": "audit_logs",
        "category": "Auditability",
        "standard": "Every material setting change, dispatch attempt, recovery action, and money-impact event must be durable.",
        "evidence": ("cas_forex/order_attempt_audit.py", "cas_forex/ai_control_authority.py", "cas_forex/risk_control.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 13,
        "key": "compliance_awareness",
        "category": "Legal/Compliance",
        "standard": "Copy and flows avoid profit guarantees and surface AI, automated trading, broker, and risk disclosures.",
        "evidence": (
            "cas_forex/professional_claims.py",
            "cas_forex/legal_review_readiness.py",
            "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md",
            "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md",
            "tests/test_legal_review_readiness.py",
            "ui/src/pages/RiskDisclosurePage.tsx",
        ),
        "gap": "Internal disclosure draft and launch-review checklist exist; external legal counsel review is not a code artifact.",
        "next_action": "Obtain legal/compliance review before public launch or advising others for compensation.",
        "partial_terms": ("external_legal_review",),
        "external_dependency": "Qualified legal/compliance review and accepted counsel record.",
    },
    {
        "item_number": 14,
        "key": "broker_legitimacy_boundary",
        "category": "Broker Boundary",
        "standard": "The UI must not imply that MT4/MT5 compatibility proves broker safety or registration.",
        "evidence": ("cas_forex/broker_reality.py", "ui/src/pages/SettingsPage.tsx", "tests/test_broker_reality.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 15,
        "key": "secrets_handling",
        "category": "Security",
        "standard": "Secrets stay server-side, masked in reports, encrypted in runtime stores, and absent from frontend bundles.",
        "evidence": (
            "cas_forex/secret_envelope.py",
            "cas_forex/managed_secret_store.py",
            "cas_forex/security_posture.py",
            "cas_forex/push_notifications.py",
            "cas_forex/webhook_notifications.py",
            "tests/test_security_posture.py",
            "tests/test_managed_secret_store.py",
            "tests/test_push_notifications.py",
            "tests/test_notifications_route.py",
            "tests/test_webhook_notifications.py",
            "ui/src/components/settings/SecurityPosturePanel.tsx:Managed Secret Store",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 16,
        "key": "backend_enforced_risk",
        "category": "Security",
        "standard": "Frontend controls are advisory; backend APIs must reject unsafe risk/order requests.",
        "evidence": ("cas_forex/order_dispatch.py", "cas_forex/runtime_gates.py", "tests/test_order_dispatch.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 17,
        "key": "role_permissions",
        "category": "Security",
        "standard": "Roles and permissions must be explicit even for a single-owner local app.",
        "evidence": (
            "cas_forex/route_permissions.py",
            "cas_forex/route_permissions.py:default_mutation_route_count",
            "cas_forex/security_posture.py",
            "api/server.py",
            "ui/src/pages/SettingsPage.tsx",
            "tests/test_route_permissions.py",
            "tests/test_security_posture.py",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 18,
        "key": "money_impact_errors",
        "category": "UX",
        "standard": "Errors must say whether broker bridge or money was touched and why an action was blocked.",
        "evidence": ("cas_forex/order_dispatch.py", "cas_forex/critical_notifications.py", "tests/test_critical_notifications.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 19,
        "key": "status_system",
        "category": "UX",
        "standard": "The app must show broker, terminal, AI, risk, recovery, dispatch, and data-source health separately.",
        "evidence": (
            "cas_forex/stack_health_check.py",
            "cas_forex/account_health.py",
            "cas_forex/operator_briefing.py",
            "api/routes/operator_briefing.py",
            "ui/src/components/CriticalAlertStrip.tsx",
            "ui/src/components/OperatorBriefingCard.tsx",
            "tests/test_operator_briefing.py",
            "tests/test_operator_briefing_route.py",
            "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 20,
        "key": "market_session_handling",
        "category": "Execution Safety",
        "standard": "Market closure, sessions, stale prices, spread/slippage, and macro/news windows must be handled gracefully.",
        "evidence": (
            "cas_forex/session_autowake_runner.py",
            "cas_forex/verifier/macro_gate.py",
            "cas_forex/order_dispatch.py:_macro_blackout_report calendar_source_status",
            "cas_forex/economic_calendar_feed.py",
            "api/routes/settings.py:/economic-calendar",
            "ui/src/pages/SettingsPage.tsx:EconomicCalendarPanel",
            "tests/test_economic_calendar_feed.py",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 21,
        "key": "broker_symbol_normalization",
        "category": "Broker Adapters",
        "standard": "Symbols, aliases, min lots, lot step, tick value, stop distance, and margin rules must be broker-aware.",
        "evidence": ("cas_forex/broker_symbol_diagnostics.py", "ui/src/pages/SettingsPage.tsx", "tests/test_broker_symbol_normalization.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 22,
        "key": "money_math_transparency",
        "category": "Risk Engine",
        "standard": "Before dispatch, estimated margin, free margin, dollar risk, spread/slippage, and account impact are visible.",
        "evidence": ("cas_forex/order_dispatch.py", "cas_forex/trade_management.py", "tests/test_order_dispatch.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 23,
        "key": "protective_order_visibility",
        "category": "Risk Engine",
        "standard": "Open trades must surface stop-loss/take-profit protection and flag unprotected positions.",
        "evidence": (
            "cas_forex/account_health.py",
            "cas_forex/order_dispatch.py",
            "cas_forex/broker_truth_monitor.py:live_position_stop_loss_protection",
            "tests/test_account_health.py",
            "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 24,
        "key": "manual_override_emergency",
        "category": "Emergency Controls",
        "standard": "Owner must be able to pause automation, stop new trades, close selected broker exposure, and cancel pending orders.",
        "evidence": ("cas_forex/emergency_controls.py", "api/routes/broker_emergency.py", "ui/src/pages/SettingsPage.tsx"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 25,
        "key": "model_version_control",
        "category": "Auditability",
        "standard": "Every decision should attach model, prompt, strategy, risk, dispatch, market-data, and config versions/hashes.",
        "evidence": ("cas_forex/execution_provenance.py", "cas_forex/agent_decision_explainer.py", "ui/src/components/DecisionVersionTrace.tsx"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 26,
        "key": "brain_execution_separation",
        "category": "Architecture",
        "standard": "AI/strategy, risk, execution, broker adapter, audit, and notification responsibilities must be separated.",
        "evidence": ("cas_forex/agent_dispatch.py", "cas_forex/order_dispatch.py", "cas_forex/critical_notifications.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 27,
        "key": "core_over_landing_page",
        "category": "Product",
        "standard": "The first screen should be the usable cockpit, not a marketing landing page.",
        "evidence": ("ui/src/App.tsx", "ui/src/pages/TradePage.tsx", "ui/src/pages/ProofPage.tsx"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 28,
        "key": "design_system_consistency",
        "category": "Frontend",
        "standard": "Shared components, radius, status chips, tables, loading, empty, and error states reduce amateur UI inconsistency.",
        "evidence": (
            "ui/src/components/GlassPanel.tsx",
            "ui/src/components/StatusChip.tsx",
            "ui/src/App.css",
            "cas_forex/ui_layout_contract.py",
            "scripts/run_ui_layout_contract.py",
            "tests/test_ui_layout_contract.py",
            "cas_forex/ui_browser_zoom_smoke.py",
            "scripts/run_ui_browser_zoom_smoke.py",
            "tests/test_ui_browser_zoom_smoke.py",
            "cas_forex/ui_visual_baseline.py",
            "scripts/run_ui_visual_baseline.py",
            "tests/test_ui_visual_baseline.py",
            "ui/visual_baselines/README.md",
            "ui/visual_baselines/cas_forex_ui_browser_zoom_baseline.json",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 29,
        "key": "decision_metrics_dashboard",
        "category": "Dashboard",
        "standard": "Account health should show equity, free margin, open risk, drawdown, PnL, exposure, win/loss, and source health.",
        "evidence": ("cas_forex/account_health.py", "ui/src/pages/TradePage.tsx", "tests/test_account_health.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 30,
        "key": "critical_notifications",
        "category": "Operations",
        "standard": "Serious events like live enabled, trade opened/closed, risk blocks, disconnection, or missing stops must alert the owner.",
        "evidence": (
            "cas_forex/critical_notifications.py:build_critical_notification_delivery_readiness",
            "cas_forex/critical_notifications.py:build_local_alert_channel_report",
            "ui/src/components/CriticalAlertStrip.tsx",
            "ui/src/pages/SettingsPage.tsx",
            "tests/test_critical_notifications.py",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 31,
        "key": "safe_onboarding",
        "category": "Onboarding",
        "standard": "Startup should guide API, UI, phone, MT4/MT5, paper/demo, diagnostics, and live prerequisites in order.",
        "evidence": (
            "ui/src/pages/QuickStartPage.tsx",
            "docs/MOBILE_APP.md",
            "cas_forex/spec_context.py",
            "api/routes/settings.py:/spec-context",
            "ui/src/pages/SettingsPage.tsx:SpecContextPanel",
            "tests/test_spec_context.py",
            "tests/test_settings_api_surface.py",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 32,
        "key": "legal_disclosures",
        "category": "Legal/Compliance",
        "standard": "Terms/risk/automated trading/AI/broker/data disclosures must exist before public use.",
        "evidence": (
            "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md",
            "docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md",
            "docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md",
            "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md",
            "ui/src/pages/RiskDisclosurePage.tsx",
            "ui/src/pages/TermsPage.tsx",
            "ui/src/pages/PrivacyPage.tsx",
            "cas_forex/professional_claims.py",
            "cas_forex/legal_review_readiness.py",
            "tests/test_legal_review_readiness.py",
            "ui/src/pages/SettingsPage.tsx:LegalReviewReadinessPanel",
        ),
        "gap": "Risk, Terms, and Privacy drafts exist in-app and in docs; counsel-approved final policy set is still needed.",
        "next_action": "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
        "partial_terms": ("counsel_review",),
        "external_dependency": "Counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures.",
    },
    {
        "item_number": 33,
        "key": "dangerous_edge_case_tests",
        "category": "Testing",
        "standard": "Tests must cover disconnects, duplicate events, invalid symbols, insufficient margin, stale data, and rejected stops.",
        "evidence": (
            "cas_forex/bypass_launch_gate.py",
            "tests/test_bypass_launch_gate.py",
            "tests/test_order_dispatch.py",
            "tests/test_broker_truth_monitor.py",
            "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces",
            "tests/test_terminal_receipt_ingest.py",
            "ui/src/pages/SettingsPage.tsx:BypassLaunchGatePanel",
        ),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 34,
        "key": "production_operations",
        "category": "Operations",
        "standard": "Health checks, logs, backup, rollback, build artifacts, and runbooks must be visible.",
        "evidence": (
            "cas_forex/operational_readiness.py",
            "cas_forex/external_monitoring.py",
            "cas_forex/external_monitoring_control.py",
            "cas_forex/public_launch_gate.py",
            "cas_forex/backup_restore.py",
            "api/routes/external_monitoring.py",
            "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
            "tests/test_operational_readiness.py",
            "tests/test_external_monitoring.py",
            "tests/test_external_monitoring_route.py",
            "tests/test_public_launch_gate.py",
            "ui/src/pages/SettingsPage.tsx:OperationalReadinessPanel",
            "ui/src/pages/SettingsPage.tsx:PublicLaunchGatePanel",
        ),
        "gap": "Local operations and external monitoring hooks are covered; real hosted uptime/error-tracking destinations still require owner deployment configuration.",
        "next_action": "Add external uptime/error monitoring before public cloud deployment.",
        "partial_terms": ("external_uptime_monitoring_configured", "error_tracking_dsn_configured"),
        "external_dependency": "Hosted uptime monitor and error-tracking DSN configured in the deployment environment.",
    },
    {
        "item_number": 35,
        "key": "transparent_performance_page",
        "category": "Performance",
        "standard": "Performance pages must separate paper/demo/live, show costs and losses, and avoid screenshot-only proof.",
        "evidence": ("cas_forex/performance_discipline.py", "ui/src/pages/StrategyComparisonPage.tsx", "ui/src/pages/LedgerPage.tsx"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 36,
        "key": "professional_language",
        "category": "Product Copy",
        "standard": "Copy should avoid money-printer claims, guaranteed profits, fake AI certainty, and hype language.",
        "evidence": ("cas_forex/professional_claims.py", "ui/src/pages/RiskDisclosurePage.tsx", "tests/test_professional_claims.py"),
        "gap": "",
        "next_action": "",
    },
    {
        "item_number": 37,
        "key": "controlled_trading_os",
        "category": "Architecture",
        "standard": "The product should behave as a controlled trading operating system, not an unconstrained AI bot.",
        "evidence": (
            "cas_forex/runtime_gates.py",
            "cas_forex/ai_control_authority.py",
            "cas_forex/order_dispatch.py",
            "cas_forex/spec_context.py",
            "cas_forex/public_launch_gate.py",
            "api/routes/settings.py:/spec-context",
            "tests/test_public_launch_gate.py",
            "tests/test_spec_context.py",
        ),
        "gap": "",
        "next_action": "",
    },
)
