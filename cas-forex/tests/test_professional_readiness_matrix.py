from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.professional_readiness_matrix import build_professional_readiness_matrix, _evidence_present
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_professional_readiness_matrix_has_37_numbered_rows():
    report = build_professional_readiness_matrix(REPO_ROOT)

    assert report["report_kind"] == "cas_forex_professional_readiness_matrix"
    assert report["item_count"] == 37
    assert len(report["rows"]) == 37
    assert [row["item_number"] for row in report["rows"]] == list(range(1, 38))
    assert report["ok_count"] + report["partial_count"] + report["gap_count"] == 37
    assert report["attention_count"] == report["partial_count"] + report["gap_count"]
    assert report["satisfied_count"] + report["internal_partial_count"] + report["external_blocked_count"] + report["missing_count"] == 37
    assert report["missing_count"] == report["gap_count"]
    assert "does not place orders" in report["claim_boundary"]


def test_professional_readiness_marker_evidence_requires_file_content(tmp_path: Path):
    evidence_file = tmp_path / "panel.tsx"
    evidence_file.write_text("export function SpecContextPanel() { return null }", encoding="utf-8")

    assert _evidence_present(tmp_path, "panel.tsx:SpecContextPanel") is True
    assert _evidence_present(tmp_path, "panel.tsx:MissingPanel") is False
    assert _evidence_present(tmp_path, "panel.tsx") is True


def test_professional_readiness_matrix_surfaces_core_trading_safety_evidence():
    report = build_professional_readiness_matrix(REPO_ROOT)
    rows = {row["key"]: row for row in report["rows"]}

    assert rows["hard_risk_engine"]["status"] == "OK"
    assert "cas_forex/pre_execution_risk_gate.py" in rows["hard_risk_engine"]["present_evidence_refs"]
    assert rows["duplicate_order_protection"]["status"] == "OK"
    assert "cas_forex/order_attempt_audit.py" in rows["duplicate_order_protection"]["present_evidence_refs"]
    assert rows["broker_state_reconciliation"]["status"] == "OK"
    assert "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces" in rows["broker_state_reconciliation"]["present_evidence_refs"]
    assert rows["secrets_handling"]["status"] == "OK"
    assert "cas_forex/managed_secret_store.py" in rows["secrets_handling"]["present_evidence_refs"]
    assert "cas_forex/push_notifications.py" in rows["secrets_handling"]["present_evidence_refs"]
    assert "cas_forex/webhook_notifications.py" in rows["secrets_handling"]["present_evidence_refs"]
    assert "tests/test_push_notifications.py" in rows["secrets_handling"]["present_evidence_refs"]
    assert "tests/test_notifications_route.py" in rows["secrets_handling"]["present_evidence_refs"]
    assert "tests/test_webhook_notifications.py" in rows["secrets_handling"]["present_evidence_refs"]
    assert "managed_secrets_store" not in rows["secrets_handling"]["partial_terms"]
    assert rows["role_permissions"]["status"] == "OK"
    assert "cas_forex/route_permissions.py" in rows["role_permissions"]["present_evidence_refs"]
    assert rows["role_permissions"]["partial_terms"] == []
    assert rows["critical_notifications"]["status"] == "OK"
    assert "cas_forex/critical_notifications.py:build_local_alert_channel_report" in rows["critical_notifications"]["present_evidence_refs"]
    assert rows["critical_notifications"]["partial_terms"] == []
    assert rows["protective_order_visibility"]["status"] == "OK"
    assert "cas_forex/broker_truth_monitor.py:live_position_stop_loss_protection" in rows["protective_order_visibility"]["present_evidence_refs"]
    assert "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces" in rows["protective_order_visibility"]["present_evidence_refs"]
    assert rows["status_system"]["status"] == "OK"
    assert "cas_forex/operator_briefing.py" in rows["status_system"]["present_evidence_refs"]
    assert "api/routes/operator_briefing.py" in rows["status_system"]["present_evidence_refs"]
    assert "ui/src/components/OperatorBriefingCard.tsx" in rows["status_system"]["present_evidence_refs"]
    assert "tests/test_operator_briefing_route.py" in rows["status_system"]["present_evidence_refs"]
    assert "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces" in rows["status_system"]["present_evidence_refs"]
    assert rows["market_session_handling"]["status"] == "OK"
    assert "cas_forex/economic_calendar_feed.py" in rows["market_session_handling"]["present_evidence_refs"]
    assert rows["market_session_handling"]["partial_terms"] == []
    assert rows["safe_onboarding"]["status"] == "OK"
    assert "cas_forex/spec_context.py" in rows["safe_onboarding"]["present_evidence_refs"]
    assert "ui/src/pages/SettingsPage.tsx:SpecContextPanel" in rows["safe_onboarding"]["present_evidence_refs"]
    assert "tests/test_spec_context.py" in rows["safe_onboarding"]["present_evidence_refs"]
    assert rows["design_system_consistency"]["status"] == "OK"
    assert "cas_forex/ui_layout_contract.py" in rows["design_system_consistency"]["present_evidence_refs"]
    assert "cas_forex/ui_browser_zoom_smoke.py" in rows["design_system_consistency"]["present_evidence_refs"]
    assert "cas_forex/ui_visual_baseline.py" in rows["design_system_consistency"]["present_evidence_refs"]
    assert "ui/visual_baselines/cas_forex_ui_browser_zoom_baseline.json" in rows["design_system_consistency"]["present_evidence_refs"]
    assert rows["design_system_consistency"]["partial_terms"] == []
    assert rows["dangerous_edge_case_tests"]["status"] == "OK"
    assert "cas_forex/bypass_launch_gate.py" in rows["dangerous_edge_case_tests"]["present_evidence_refs"]
    assert "tests/test_bypass_launch_gate.py" in rows["dangerous_edge_case_tests"]["present_evidence_refs"]
    assert "tests/test_broker_truth_cross_surface.py:test_broker_truth_paper_force_condition_is_consistent_across_owner_surfaces" in rows["dangerous_edge_case_tests"]["present_evidence_refs"]
    assert rows["production_operations"]["status"] == "PARTIAL"
    assert rows["production_operations"]["completion_state"] == "EXTERNAL_BLOCKED"
    assert rows["production_operations"]["blocked_by_external_dependency"] is True
    assert "cas_forex/external_monitoring.py" in rows["production_operations"]["present_evidence_refs"]
    assert "cas_forex/public_launch_gate.py" in rows["production_operations"]["present_evidence_refs"]
    assert "tests/test_external_monitoring.py" in rows["production_operations"]["present_evidence_refs"]
    assert "tests/test_public_launch_gate.py" in rows["production_operations"]["present_evidence_refs"]
    assert rows["compliance_awareness"]["status"] == "PARTIAL"
    assert rows["compliance_awareness"]["completion_state"] == "EXTERNAL_BLOCKED"
    assert rows["compliance_awareness"]["blocked_by_external_dependency"] is True
    assert rows["compliance_awareness"]["next_action"] == (
        "Complete qualified legal/compliance review and add an accepted counsel review record before public launch."
    )
    assert "cas_forex/legal_review_readiness.py" in rows["compliance_awareness"]["present_evidence_refs"]
    assert "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md" in rows["compliance_awareness"]["present_evidence_refs"]
    assert "tests/test_legal_review_readiness.py" in rows["compliance_awareness"]["present_evidence_refs"]
    assert rows["legal_disclosures"]["status"] == "PARTIAL"
    assert rows["legal_disclosures"]["completion_state"] == "EXTERNAL_BLOCKED"
    assert rows["legal_disclosures"]["blocked_by_external_dependency"] is True
    assert rows["legal_disclosures"]["next_action"] == (
        "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch."
    )
    assert "cas_forex/legal_review_readiness.py" in rows["legal_disclosures"]["present_evidence_refs"]
    assert "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md" in rows["legal_disclosures"]["present_evidence_refs"]
    assert "ui/src/pages/SettingsPage.tsx:LegalReviewReadinessPanel" in rows["legal_disclosures"]["present_evidence_refs"]
    assert rows["controlled_trading_os"]["status"] == "OK"
    assert "cas_forex/public_launch_gate.py" in rows["controlled_trading_os"]["present_evidence_refs"]
    assert "cas_forex/spec_context.py" in rows["controlled_trading_os"]["present_evidence_refs"]
    assert "tests/test_public_launch_gate.py" in rows["controlled_trading_os"]["present_evidence_refs"]
    assert report["external_blocked_count"] == 3
    assert report["internal_partial_count"] == 0
    assert report["missing_count"] == 0


def test_professional_readiness_matrix_dynamic_rows_can_turn_ok(monkeypatch):
    import cas_forex.professional_readiness_matrix as prm

    monkeypatch.setattr(
        prm,
        "build_legal_review_readiness",
        lambda base: {
            "status": "OK",
            "counsel_review_accepted": True,
            "next_action": "Counsel-reviewed launch record is accepted.",
        },
    )
    monkeypatch.setattr(
        prm,
        "build_operational_readiness_report",
        lambda base, env=None: {
            "status": "OK",
            "attention_items": [],
            "external_monitoring": {
                "status": "OK",
                "checks": [
                    {"key": "external_uptime_monitor", "status": "OK"},
                    {"key": "error_tracking_dsn", "status": "OK"},
                ],
                "top_attention_items": [],
                "next_action": "External hooks are configured.",
            },
        },
    )

    report = prm.build_professional_readiness_matrix(REPO_ROOT)
    rows = {row["key"]: row for row in report["rows"]}

    assert report["attention_count"] == 0
    assert report["external_blocked_count"] == 0
    assert report["satisfied_count"] == 37
    assert rows["compliance_awareness"]["status"] == "OK"
    assert rows["compliance_awareness"]["completion_state"] == "SATISFIED"
    assert rows["legal_disclosures"]["status"] == "OK"
    assert rows["legal_disclosures"]["completion_state"] == "SATISFIED"
    assert rows["production_operations"]["status"] == "OK"
    assert rows["production_operations"]["completion_state"] == "SATISFIED"


def test_professional_readiness_top_attention_items_are_deduplicated(monkeypatch):
    import cas_forex.professional_readiness_matrix as prm

    monkeypatch.setattr(
        prm,
        "build_legal_review_readiness",
        lambda base: {
            "status": "ATTENTION",
            "counsel_review_accepted": False,
            "next_action": "Complete qualified legal/compliance review and add an accepted counsel review record before public launch.",
        },
    )
    monkeypatch.setattr(
        prm,
        "build_operational_readiness_report",
        lambda base, env=None: {
            "status": "ATTENTION",
            "attention_items": ["Configure external uptime monitoring."],
            "external_monitoring": {
                "status": "ATTENTION",
                "checks": [
                    {"key": "external_uptime_monitor", "status": "MISSING"},
                    {"key": "error_tracking_dsn", "status": "MISSING"},
                ],
                "top_attention_items": ["Configure external uptime monitoring."],
                "next_action": "Configure external uptime monitoring, error tracking, and off-screen alert destinations before hosted production.",
            },
        },
    )

    report = prm.build_professional_readiness_matrix(REPO_ROOT)

    assert report["top_attention_items"] == [
        "Complete qualified legal/compliance review and add an accepted counsel review record before public launch.",
        "Obtain counsel-reviewed final Terms, Privacy, risk, automated trading, AI, and broker disclosures before public launch.",
        "Configure external uptime monitoring, error tracking, and off-screen alert destinations before hosted production.",
    ]


def test_professional_readiness_route_is_cache_first_and_read_only(monkeypatch):
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

    body = asyncio.run(settings_route.get_professional_readiness())

    assert captured == {
        "key": "settings_professional_readiness",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_professional_readiness_matrix"
    assert body["status"] == "WARMING"
    assert "does not place orders" in body["claim_boundary"]


def test_professional_readiness_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("ProfessionalReadinessPanel")
    # Moved to components/settings/ProfessionalReadinessPanel.tsx in the settings decomposition (slice 2).
    extracted_professionalreadinesspanel = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "ProfessionalReadinessPanel.tsx").read_text(encoding="utf-8")
    assert "Professional Readiness Matrix" in extracted_professionalreadinesspanel
    assert "37-item audit" in extracted_professionalreadinesspanel
    assert "fetchProfessionalReadiness" in extracted_professionalreadinesspanel
    assert "ProfessionalReadinessMatrix" in api_client
    assert "external_blocked_count" in api_client
    assert "completion_state" in api_client
    assert "blocked_by_external_dependency" in api_client
    assert '"/settings/professional-readiness"' in api_client
    assert_panel_wired("SpecContextPanel")
    # Moved to components/settings/SpecContextPanel.tsx in the settings decomposition (slice 2).
    extracted_speccontextpanel = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "SpecContextPanel.tsx").read_text(encoding="utf-8")
    assert "Spec Context" in extracted_speccontextpanel
    assert "fetchSpecContextStatus" in extracted_speccontextpanel
    assert "SpecContextStatusReport" in api_client
    assert '"/settings/spec-context"' in api_client
    assert_panel_wired("LegalReviewReadinessPanel")
    # Moved to components/settings/LegalGovernancePanels.tsx in the settings decomposition.
    extracted_legalgovernancepanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "LegalGovernancePanels.tsx").read_text(encoding="utf-8")
    assert "Legal Review Readiness" in extracted_legalgovernancepanels
    assert "fetchLegalReviewReadiness" in extracted_legalgovernancepanels
    assert "LegalReviewReadinessReport" in api_client
    assert '"/settings/legal-review-readiness"' in api_client
    assert_panel_wired("PublicLaunchGatePanel")
    # Moved to components/settings/LaunchGatePanels.tsx in the settings decomposition (slice 2).
    extracted_launchgatepanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "LaunchGatePanels.tsx").read_text(encoding="utf-8")
    assert "Public Launch Gate" in extracted_launchgatepanels
    assert "fetchPublicLaunchGate" in extracted_launchgatepanels
    assert "PublicLaunchGateReport" in api_client
    assert '"/settings/public-launch-gate"' in api_client
    assert_panel_wired("BypassLaunchGatePanel")
    assert "Bypass Launch Gate" in extracted_launchgatepanels
    assert "fetchBypassLaunchGate" in extracted_launchgatepanels
    assert "BypassLaunchGateReport" in api_client
    assert '"/settings/bypass-launch-gate"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/spec-context") is False
    assert api_server._should_trace_request("GET", "/api/forex/settings/legal-review-readiness") is False
    assert api_server._should_trace_request("GET", "/api/forex/settings/public-launch-gate") is False
    assert api_server._should_trace_request("GET", "/api/forex/settings/professional-readiness") is False
    assert api_server._should_trace_request("GET", "/api/forex/settings/bypass-launch-gate") is False
