from __future__ import annotations

import asyncio
import hashlib

import pytest

from api.routes import settings as settings_route
from cas_forex.legal_review_control import (
    LegalReviewControlError,
    RECORD_CONFIRM_PHRASE,
    build_legal_review_control_report,
    reset_counsel_review_record,
    set_legal_review_paths_for_tests,
    write_counsel_review_record,
)
from cas_forex.legal_review_readiness import build_legal_review_readiness


def _write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_draft_package(root) -> None:
    _write(root / "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md", "Risk Disclosure\nAutomated trading can lose money.\n")
    _write(root / "docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md", "Terms\nNo profit guarantee.\n")
    _write(root / "docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md", "Privacy\nData deletion and retention.\n")
    _write(
        root / "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md",
        (
            "public launch\n"
            "counsel\n"
            "jurisdiction\n"
            "automated trading\n"
            "retail forex\n"
            "privacy\n"
            "broker\n"
            "risk disclosure\n"
        ),
    )


def test_write_counsel_review_record_computes_local_artifact_hash_and_turns_readiness_ok(tmp_path):
    _write_draft_package(tmp_path)
    artifact = tmp_path / "evidence" / "counsel-review.txt"
    _write(artifact, "external counsel review evidence")

    report = write_counsel_review_record(
        root=tmp_path,
        reviewed_by="Example Legal LLP",
        review_date="2026-07-09",
        scope="Terms, risk disclosure, privacy, automated trading, broker connectivity, retail forex, public launch",
        review_artifact_path=str(artifact),
        qualified_counsel_confirmed=True,
        confirm_phrase=RECORD_CONFIRM_PHRASE,
    )

    expected_hash = hashlib.sha256(b"external counsel review evidence").hexdigest()
    current = report["current_record"]
    readiness = build_legal_review_readiness(tmp_path)

    assert report["file_present"] is True
    assert current["review_artifact_sha256"] == expected_hash
    assert current["qualified_counsel_confirmed"] is True
    assert readiness["status"] == "OK"
    assert readiness["counsel_review_accepted"] is True


def test_write_counsel_review_record_requires_typed_confirmation(tmp_path):
    artifact = tmp_path / "evidence" / "counsel-review.txt"
    _write(artifact, "external counsel review evidence")

    with pytest.raises(LegalReviewControlError, match="Typed confirmation"):
        write_counsel_review_record(
            root=tmp_path,
            reviewed_by="Example Legal LLP",
            review_date="2026-07-09",
            scope="Terms, risk disclosure, privacy, automated trading, broker connectivity",
            review_artifact_path=str(artifact),
            qualified_counsel_confirmed=True,
            confirm_phrase="WRONG PHRASE",
        )


def test_settings_legal_review_control_update_route_writes_record_and_returns_fresh_packets(tmp_path, monkeypatch):
    record_path = tmp_path / "docs" / "legal" / "CAS_FOREX_COUNSEL_REVIEW_RECORD.md"
    audit_path = tmp_path / "runtime" / "legal-review-record-audit.jsonl"
    artifact = tmp_path / "evidence" / "counsel-review.txt"
    _write(artifact, "external counsel review evidence")
    set_legal_review_paths_for_tests(record_path, audit_path)
    monkeypatch.setattr(
        settings_route,
        "build_legal_review_readiness",
        lambda: {"report_kind": "cas_forex_legal_review_readiness", "status": "ATTENTION"},
    )
    monkeypatch.setattr(
        settings_route,
        "build_professional_readiness_matrix",
        lambda: {"report_kind": "cas_forex_professional_readiness_matrix", "status": "ATTENTION"},
    )
    monkeypatch.setattr(
        settings_route,
        "build_public_launch_gate",
        lambda reports=None: {"report_kind": "cas_forex_public_launch_gate", "status": "ATTENTION"},
    )
    try:
        body = asyncio.run(
            settings_route.post_legal_review_control_update(
                settings_route.LegalReviewControlUpdate(
                    reviewed_by="Example Legal LLP",
                    review_date="2026-07-09",
                    scope="Terms, risk disclosure, privacy, automated trading, broker connectivity, retail forex, public launch",
                    review_artifact_path=str(artifact),
                    qualified_counsel_confirmed=True,
                    confirm_phrase=RECORD_CONFIRM_PHRASE,
                )
            )
        )
        persisted = record_path.read_text(encoding="utf-8")
    finally:
        set_legal_review_paths_for_tests(None, None)

    assert body["status"] == "UPDATED"
    assert body["required_confirm_phrase"] == RECORD_CONFIRM_PHRASE
    assert "Example Legal LLP" in persisted
    assert "review_artifact_sha256:" in persisted
    assert body["legal_review_control"]["file_present"] is True


def test_settings_legal_review_control_reset_route_clears_record(tmp_path, monkeypatch):
    record_path = tmp_path / "docs" / "legal" / "CAS_FOREX_COUNSEL_REVIEW_RECORD.md"
    audit_path = tmp_path / "runtime" / "legal-review-record-audit.jsonl"
    set_legal_review_paths_for_tests(record_path, audit_path)
    try:
        write_counsel_review_record(
            reviewed_by="Example Legal LLP",
            review_date="2026-07-09",
            scope="Terms, risk disclosure, privacy, automated trading, broker connectivity, retail forex, public launch",
            review_artifact_path="C:/legal/cas-forex-review.pdf",
            review_artifact_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            qualified_counsel_confirmed=True,
            confirm_phrase=RECORD_CONFIRM_PHRASE,
        )
        monkeypatch.setattr(
            settings_route,
            "build_legal_review_readiness",
            lambda: {"report_kind": "cas_forex_legal_review_readiness", "status": "ATTENTION"},
        )
        monkeypatch.setattr(
            settings_route,
            "build_professional_readiness_matrix",
            lambda: {"report_kind": "cas_forex_professional_readiness_matrix", "status": "ATTENTION"},
        )
        monkeypatch.setattr(
            settings_route,
            "build_public_launch_gate",
            lambda reports=None: {"report_kind": "cas_forex_public_launch_gate", "status": "ATTENTION"},
        )
        body = asyncio.run(settings_route.post_legal_review_control_reset())
    finally:
        set_legal_review_paths_for_tests(None, None)

    assert body["status"] == "RESET"
    assert record_path.exists() is False
    assert body["legal_review_control"]["file_present"] is False
    assert audit_path.exists() is True


def test_build_legal_review_control_report_is_read_only(tmp_path):
    report = build_legal_review_control_report(tmp_path)

    assert report["report_kind"] == "cas_forex_legal_review_control"
    assert report["required_confirm_phrase"] == RECORD_CONFIRM_PHRASE
    assert "does not provide legal advice" in report["claim_boundary"]
    assert report["file_present"] is False
    assert report["current_record"]["review_artifact_sha256"] == ""


def test_settings_legal_review_control_get_route_is_cache_first_and_read_only(monkeypatch):
    captured = {}

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

    body = asyncio.run(settings_route.get_legal_review_control())

    assert captured == {
        "key": "settings_legal_review_control",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_legal_review_control"
    assert body["status"] == "WARMING"
    assert body["required_confirm_phrase"] == RECORD_CONFIRM_PHRASE
