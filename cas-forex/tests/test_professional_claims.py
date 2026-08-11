from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.professional_claims import build_professional_claims_report
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_minimum_disclosure(root: Path) -> None:
    _write(
        root / "docs" / "legal" / "CAS_FOREX_DISCLOSURE_DRAFT.md",
        "\n".join(
            [
                "No guarantee of profit.",
                "Automated trading risk.",
                "AI limitations.",
                "Broker execution boundary.",
                "Paper demo live separation.",
                "Not financial advice.",
            ]
        ),
    )


def test_professional_claims_detects_risky_copy_and_boundary_references(tmp_path):
    _write_minimum_disclosure(tmp_path)
    _write(
        tmp_path / "ui" / "src" / "BadCopy.tsx",
        'export const headline = "AI beats the market and you never lose";\n',
    )
    _write(
        tmp_path / "api" / "routes" / "safe_copy.py",
        'SAFE = "No Profit Guarantee: no guarantee of profit."\n',
    )

    report = build_professional_claims_report(tmp_path)

    assert report["report_kind"] == "cas_forex_professional_claims"
    assert report["status"] == "ATTENTION"
    assert report["risky_claim_count"] >= 1
    assert any(hit["severity"] == "needs_review" for hit in report["claim_hits"])
    assert any(hit["severity"] == "boundary_reference" for hit in report["claim_hits"])
    assert report["disclosure_document"]["present"] is True
    assert report["missing_disclosures"] == []
    assert any("AI beats the market" in hit["excerpt"] for hit in report["claim_hits"])


def test_professional_claims_ok_when_disclosures_exist_and_copy_is_bounded(tmp_path):
    _write_minimum_disclosure(tmp_path)
    _write(
        tmp_path / "ui" / "src" / "GoodCopy.tsx",
        'export const copy = "Risk-managed automated execution with user-defined limits.";\n',
    )

    report = build_professional_claims_report(tmp_path)

    assert report["status"] == "OK"
    assert report["risky_claim_count"] == 0
    assert all(row["status"] == "COVERED" for row in report["required_disclosures"])
    assert "raw" not in str(report["disclosure_document"]).lower()


def test_repo_professional_claims_report_has_no_risky_app_claims():
    report = build_professional_claims_report(REPO_ROOT)

    risky_hits = [hit for hit in report["claim_hits"] if hit["severity"] == "needs_review"]
    assert risky_hits == []
    assert report["risky_claim_count"] == 0
    assert report["missing_disclosures"] == []


def test_professional_claims_route_is_cache_first_and_read_only(monkeypatch):
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

    body = asyncio.run(settings_route.get_professional_claims())

    assert captured == {
        "key": "settings_professional_claims",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_professional_claims"
    assert body["status"] == "WARMING"
    assert "promise returns" in body["claim_boundary"]


def test_professional_claims_settings_ui_and_trace_skip_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("ProfessionalClaimsPanel")
    assert "Professional Claims & Disclosures" in settings_page
    assert "fetchProfessionalClaims" in settings_page
    assert "ProfessionalClaimsReport" in api_client
    assert '"/settings/professional-claims"' in api_client
    assert api_server._should_trace_request("GET", "/api/forex/settings/professional-claims") is False
