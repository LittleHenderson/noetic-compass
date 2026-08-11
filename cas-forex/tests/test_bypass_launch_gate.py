from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.bypass_launch_gate import build_bypass_launch_gate_report
from cas_forex.professional_readiness_matrix import build_professional_readiness_matrix
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bypass_launch_gate_reports_all_core_no_bypass_invariants_ok():
    report = build_bypass_launch_gate_report(REPO_ROOT)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["report_kind"] == "cas_forex_bypass_launch_gate"
    assert report["status"] == "OK"
    assert report["launch_gate_status"] == "PASS"
    assert report["ok_count"] == report["check_count"] >= 8
    assert report["attention_count"] == 0
    assert "does not run pytest" in report["claim_boundary"]

    for check_id in (
        "route_permission_sensitive_routes",
        "single_order_dispatch_chokepoint",
        "edge_pass_fresh_one_use_bound",
        "fresh_broker_truth_before_real_dispatch",
        "manual_live_order_typed_confirmation",
        "manual_order_anti_impulse_before_quote",
        "money_movement_requires_owner_gates",
        "snapshot_routes_read_only",
    ):
        assert checks[check_id]["status"] == "OK"
        assert checks[check_id]["missing_evidence_refs"] == []
        assert checks[check_id]["missing_required_terms"] == []
        assert checks[check_id]["forbidden_term_hits"] == []


def test_bypass_launch_gate_catches_missing_evidence(tmp_path):
    report = build_bypass_launch_gate_report(tmp_path)

    assert report["status"] == "ATTENTION"
    assert report["launch_gate_status"] == "BLOCK_RELEASE"
    assert report["attention_count"] == report["check_count"]
    assert report["top_attention_items"]


def test_bypass_launch_gate_route_is_cache_first_and_read_only(monkeypatch):
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

    body = asyncio.run(settings_route.get_bypass_launch_gate())

    assert captured == {
        "key": "settings_bypass_launch_gate",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_bypass_launch_gate"
    assert body["status"] == "WARMING"
    assert "does not run pytest" in body["claim_boundary"]


def test_bypass_launch_gate_is_in_professional_readiness_item_33_and_settings_ui():
    matrix = build_professional_readiness_matrix(REPO_ROOT)
    rows = {row["key"]: row for row in matrix["rows"]}
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert rows["dangerous_edge_case_tests"]["status"] == "OK"
    assert "cas_forex/bypass_launch_gate.py" in rows["dangerous_edge_case_tests"]["present_evidence_refs"]
    assert "tests/test_bypass_launch_gate.py" in rows["dangerous_edge_case_tests"]["present_evidence_refs"]
    assert_panel_wired("BypassLaunchGatePanel")
    assert "Bypass Launch Gate" in settings_page
    assert "fetchBypassLaunchGate" in settings_page
    assert "BypassLaunchGateReport" in api_client
    assert '"/settings/bypass-launch-gate"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/bypass-launch-gate") is False
