from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.legal_review_readiness import build_legal_review_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_draft_package(root: Path) -> None:
    _write(root / "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md", "Risk Disclosure\nAutomated trading can lose money.\n")
    _write(root / "docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md", "Terms\nNo profit guarantee.\n")
    _write(root / "docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md", "Privacy\nData deletion and retention.\n")
    _write(root / "docs/legal/CAS_FOREX_AUTOMATED_TRADING_DISCLOSURE_DRAFT.md", "Automated trading\nStanding authority and runtime gates.\n")
    _write(root / "docs/legal/CAS_FOREX_AI_LIMITATIONS_DISCLOSURE_DRAFT.md", "AI limitations\nAI can be wrong.\n")
    _write(root / "docs/legal/CAS_FOREX_BROKER_CONNECTIVITY_DISCLOSURE_DRAFT.md", "Broker connectivity\nBroker/provider state is the source of truth.\n")
    _write(
        root / "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md",
        (
            "public launch\n"
            "counsel\n"
            "jurisdiction\n"
            "automated trading\n"
            "autonomous execution\n"
            "retail forex\n"
            "privacy\n"
            "broker\n"
            "money movement\n"
            "risk disclosure\n"
        ),
    )
    _write(
        root / "docs/working/cas_forex_autonomous_execution_correction_2026-07-09.yaml",
        "version: 2026-07-09-AUTONOMOUS-EXECUTION-CORRECTION\n",
    )


def test_legal_review_readiness_blocks_public_launch_without_counsel_record(tmp_path):
    _write_draft_package(tmp_path)

    report = build_legal_review_readiness(tmp_path)

    assert report["report_kind"] == "cas_forex_legal_review_readiness"
    assert report["status"] == "ATTENTION"
    assert report["launch_legal_status"] == "BLOCK_PUBLIC_LAUNCH"
    assert report["counsel_review_accepted"] is False
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["draft_disclosure_package"]["status"] == "OK"
    assert checks["legal_review_checklist"]["status"] == "OK"
    assert checks["counsel_review_record"]["status"] == "MISSING"
    handoff = report["counsel_review_handoff"]
    assert handoff["status"] == "COUNSEL_REVIEW_REQUIRED"
    assert handoff["launch_legal_status"] == "BLOCK_PUBLIC_LAUNCH"
    assert "counsel_review_record" in handoff["attention_keys"]
    assert any(
        doc["path"].endswith("cas_forex_autonomous_execution_correction_2026-07-09.yaml")
        for doc in handoff["package_documents"]
    )
    assert any(
        doc["path"].endswith("CAS_FOREX_AUTOMATED_TRADING_DISCLOSURE_DRAFT.md")
        for doc in handoff["package_documents"]
    )
    assert "counsel_review_status: accepted" in handoff["required_record_fields"]
    assert "money movement" in handoff["required_scope_terms"]
    assert "review_artifact_sha256: <64-character sha256>" in handoff["record_template"]
    assert "does not provide legal advice" in handoff["claim_boundary"]
    assert "CAS_FOREX_COUNSEL_REVIEW_RECORD.md" in str(report["top_attention_items"]) or report["top_attention_items"]
    assert "does not provide legal advice" in report["claim_boundary"]


def test_legal_review_readiness_ok_with_accepted_counsel_record(tmp_path):
    _write_draft_package(tmp_path)
    _write(
        tmp_path / "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        (
            "counsel_review_status: accepted\n"
            "reviewed_by: Example Legal LLP\n"
            "review_date: 2026-07-08\n"
            "scope: Terms, risk disclosure, privacy, automated trading, AI limitations, autonomous execution, broker connectivity, money movement, retail forex, public launch\n"
            "qualified_counsel_confirmed: yes\n"
            "review_artifact_path: C:/legal/cas-forex-review.pdf\n"
            "review_artifact_sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n"
        ),
    )

    report = build_legal_review_readiness(tmp_path)

    assert report["status"] == "OK"
    assert report["launch_legal_status"] == "READY_FOR_PUBLIC_LAUNCH_LEGAL"
    assert report["counsel_review_accepted"] is True
    assert report["attention_count"] == 0
    assert report["counsel_review_handoff"]["status"] == "READY_FOR_RECORD_REVIEW"
    assert report["counsel_review_handoff"]["attention_keys"] == []
    assert report["counsel_review_handoff"]["package_documents"][0]["present"] is True
    assert any(
        doc["path"].endswith("cas_forex_autonomous_execution_correction_2026-07-09.yaml") and doc["present"] is True
        for doc in report["counsel_review_handoff"]["package_documents"]
    )


def test_legal_review_readiness_requires_artifact_hash_and_external_confirmation(tmp_path):
    _write_draft_package(tmp_path)
    _write(
        tmp_path / "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md",
        (
            "counsel_review_status: accepted\n"
            "reviewed_by: Example Legal LLP\n"
            "review_date: 2026-07-08\n"
            "scope: Terms, risk disclosure, privacy, automated trading, AI limitations, autonomous execution, broker connectivity, retail forex, public launch\n"
            "review_artifact_path: C:/legal/cas-forex-review.pdf\n"
        ),
    )

    report = build_legal_review_readiness(tmp_path)

    assert report["status"] == "ATTENTION"
    assert report["counsel_review_accepted"] is False
    checks = {check["key"]: check for check in report["checks"]}
    assert checks["counsel_review_record"]["status"] == "MISSING"
    assert "qualified_counsel_confirmed: yes" in checks["counsel_review_record"]["missing_terms"]
    assert "review_artifact_sha256" in checks["counsel_review_record"]["missing_terms"]
    assert "scope:money movement" in checks["counsel_review_record"]["missing_terms"]


def test_legal_review_readiness_route_is_cache_first_and_read_only(monkeypatch):
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

    body = asyncio.run(settings_route.get_legal_review_readiness())

    assert captured == {
        "key": "settings_legal_review_readiness",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_legal_review_readiness"
    assert body["status"] == "WARMING"
    assert body["launch_legal_status"] == "WARMING"
    assert body["counsel_review_accepted"] is False
    assert "does not provide legal advice" in body["claim_boundary"]


def test_legal_review_readiness_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert "<LegalReviewReadinessPanel />" in settings_page
    assert "function LegalReviewReadinessPanel()" in settings_page
    assert "Legal Review Readiness" in settings_page
    assert "Counsel Handoff" in settings_page
    assert "Package Docs" in settings_page
    assert "Required Fields" in settings_page
    assert "Record Template" in settings_page
    assert "fetchLegalReviewReadiness" in settings_page
    assert "LegalReviewReadinessReport" in api_client
    assert "LegalReviewCounselHandoff" in api_client
    assert "counsel_review_handoff" in api_client
    assert "required_record_fields" in api_client
    assert '"/settings/legal-review-readiness"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/legal-review-readiness") is False
