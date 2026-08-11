from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.public_launch_gate import build_public_launch_gate


REPO_ROOT = Path(__file__).resolve().parents[1]


def _passing_reports() -> dict[str, dict[str, Any]]:
    return {
        "professional_readiness": {
            "report_kind": "cas_forex_professional_readiness_matrix",
            "status": "OK",
            "ok_count": 37,
            "partial_count": 0,
            "gap_count": 0,
            "top_attention_items": [],
        },
        "legal_review": {
            "report_kind": "cas_forex_legal_review_readiness",
            "status": "OK",
            "launch_legal_status": "READY_FOR_PUBLIC_LAUNCH_LEGAL",
            "counsel_review_accepted": True,
            "counsel_review_record_path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        },
        "bypass_launch_gate": {
            "report_kind": "cas_forex_bypass_launch_gate",
            "status": "OK",
            "launch_gate_status": "PASS",
            "attention_count": 0,
            "top_attention_items": [],
        },
        "operational_readiness": {
            "report_kind": "cas_forex_operational_readiness",
            "status": "OK",
            "attention_count": 0,
            "attention_items": [],
            "runbook_path": "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md",
            "external_monitoring": {
                "report_kind": "cas_forex_external_monitoring_readiness",
                "status": "OK",
                "attention_count": 0,
                "required_env": {},
                "top_attention_items": [],
            },
        },
        "security_posture": {
            "report_kind": "cas_forex_security_posture",
            "status": "OK",
            "attention_items": [],
            "managed_secret_store": {"status": "OK"},
        },
        "emergency_controls": {
            "report_kind": "cas_forex_emergency_controls",
            "status": "OK",
            "attention_count": 0,
            "broker_exposure_gap": False,
            "automation_stop_ok": True,
        },
        "professional_claims": {
            "report_kind": "cas_forex_professional_claims",
            "status": "OK",
            "risky_claim_count": 0,
            "missing_disclosures": [],
            "boundary_reference_count": 0,
        },
    }


def test_public_launch_gate_passes_only_when_every_source_gate_passes():
    report = build_public_launch_gate(reports=_passing_reports())

    assert report["report_kind"] == "cas_forex_public_launch_gate"
    assert report["status"] == "OK"
    assert report["launch_gate_status"] == "PASS"
    assert report["public_launch_status"] == "READY"
    assert report["live_money_production_status"] == "READY"
    assert report["block_count"] == 0
    assert report["hard_blocker_count"] == 0
    assert report["pass_count"] == report["gate_count"] == 8
    assert all(gate["status"] == "PASS" for gate in report["gates"])
    assert "does not provide legal advice" in report["claim_boundary"]


def test_public_launch_gate_fails_closed_on_legal_or_monitoring_blockers():
    reports = _passing_reports()
    reports["legal_review"] = {
        "report_kind": "cas_forex_legal_review_readiness",
        "status": "ATTENTION",
        "launch_legal_status": "BLOCK_PUBLIC_LAUNCH",
        "counsel_review_accepted": False,
        "counsel_review_record_path": "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
    }
    reports["external_monitoring"] = {
        "report_kind": "cas_forex_external_monitoring_readiness",
        "status": "ATTENTION",
        "attention_count": 2,
        "required_env": {"uptime_monitor_any_of": ["CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL"]},
        "top_attention_items": ["Configure external uptime monitoring."],
    }

    report = build_public_launch_gate(reports=reports)

    assert report["status"] == "ATTENTION"
    assert report["launch_gate_status"] == "BLOCK_PUBLIC_LAUNCH"
    assert report["public_launch_status"] == "BLOCKED"
    assert report["live_money_production_status"] == "BLOCKED"
    gates = {gate["key"]: gate for gate in report["gates"]}
    assert gates["legal_review"]["status"] == "BLOCK"
    assert gates["external_monitoring"]["status"] == "BLOCK"
    assert report["block_count"] == 2
    assert report["hard_blocker_count"] == 2
    assert report["hard_blockers"]


def test_public_launch_gate_threads_env_into_professional_readiness_builder(monkeypatch):
    import cas_forex.public_launch_gate as plg

    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        plg,
        "build_professional_readiness_matrix",
        lambda base, env=None: (
            captured.update({"base": base, "env": env}) or _passing_reports()["professional_readiness"]
        ),
    )
    monkeypatch.setattr(plg, "build_legal_review_readiness", lambda base: _passing_reports()["legal_review"])
    monkeypatch.setattr(plg, "build_bypass_launch_gate_report", lambda base: _passing_reports()["bypass_launch_gate"])
    monkeypatch.setattr(
        plg,
        "build_operational_readiness_report",
        lambda base, env=None: _passing_reports()["operational_readiness"],
    )
    monkeypatch.setattr(plg, "build_security_posture_report", lambda: _passing_reports()["security_posture"])
    monkeypatch.setattr(plg, "build_emergency_controls_report", lambda base: _passing_reports()["emergency_controls"])
    monkeypatch.setattr(plg, "build_professional_claims_report", lambda: _passing_reports()["professional_claims"])

    env = {"CAS_FOREX_EXTERNAL_UPTIME_MONITOR_URL": "https://healthchecks.example/ping"}
    report = plg.build_public_launch_gate(REPO_ROOT, env=env)

    assert report["launch_gate_status"] == "PASS"
    assert captured["base"] == REPO_ROOT
    assert captured["env"] == env


def test_current_public_launch_gate_blocks_until_external_owner_artifacts_exist():
    report = build_public_launch_gate(REPO_ROOT)

    assert report["launch_gate_status"] == "BLOCK_PUBLIC_LAUNCH"
    gates = {gate["key"]: gate for gate in report["gates"]}
    assert gates["legal_review"]["status"] == "BLOCK"
    assert gates["professional_readiness_matrix"]["status"] == "BLOCK"
    assert report["hard_blockers"]


def test_public_launch_gate_route_is_cache_first_and_read_only(monkeypatch):
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

    body = asyncio.run(settings_route.get_public_launch_gate())

    assert captured == {
        "key": "settings_public_launch_gate",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_public_launch_gate"
    assert body["status"] == "WARMING"
    assert body["launch_gate_status"] == "WARMING"
    assert "does not provide legal advice" in body["claim_boundary"]


def test_public_launch_gate_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "<PublicLaunchGatePanel />" in settings_page
    assert "function PublicLaunchGatePanel()" in settings_page
    assert "Public Launch Gate" in settings_page
    assert "fetchPublicLaunchGate" in settings_page
    assert "PublicLaunchGateReport" in api_client
    assert '"/settings/public-launch-gate"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/public-launch-gate") is False
