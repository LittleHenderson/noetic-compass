from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.routes import mobile as mobile_route
from api.server import app


def _raw_session_payload() -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_phone_verification_session",
        "status": "external_proof_pending",
        "summary": "Phone package is ready; 3 external verification gate(s) remain.",
        "owner_token": "secret-token",
        "pairing_context": {
            "redacted_pairing_url": (
                "http://10.0.0.6:4173/?page=quick-start"
                "#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex"
            ),
            "redacted_native_pairing_url": (
                "casforex://pair?cas_owner_token=secret-token"
                "&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex"
            ),
        },
        "proof_state": {"docker_engine_status": "external"},
    }


def test_mobile_verification_session_latest_route_redacts_and_reports_default_paths(monkeypatch) -> None:
    mobile_route._mobile_evidence_cache.clear()
    monkeypatch.setattr(mobile_route, "build_phone_verification_session", _raw_session_payload)

    response = TestClient(app).get("/api/forex/mobile/verification-session/latest")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert payload["report_kind"] == "cas_forex_phone_verification_session"
    assert payload["status"] == "external_proof_pending"
    assert Path(payload["default_output_paths"]["json_path"]).parts[-4:] == (
        "evidence_runs",
        "phone_verification_session",
        "latest",
        "phone_verification_session.json",
    )
    assert Path(payload["default_output_paths"]["readme_path"]).parts[-4:] == (
        "evidence_runs",
        "phone_verification_session",
        "latest",
        "README.md",
    )
    assert payload["owner_token"] == "REDACTED"
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_mobile_proof_session_latest_route_redacts_current_gate_checklist(monkeypatch) -> None:
    mobile_route._mobile_evidence_cache.clear()

    def fake_to_dict(session: object) -> dict[str, Any]:  # noqa: ARG001
        return {
            "report_kind": "cas_forex_mobile_external_proof_session",
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external proof gate(s) remain.",
            "owner_token": "secret-token",
            "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
            "package_ready_for_phone_install": True,
            "gates": [
                {
                    "gate_id": "phone_browser_proof",
                    "title": "Real phone Quick Start proof",
                    "satisfied": False,
                    "command": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                    "target_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
                    "detail": "Open Quick Start from the real phone.",
                }
            ],
            "remaining_external_gates": ["Real phone Quick Start proof"],
            "owner_commands": {"mobile_proof_session": "npm --prefix ui run mobile:proof-session"},
        }

    monkeypatch.setattr(mobile_route, "build_mobile_proof_session", lambda: SimpleNamespace(status="unused"))
    monkeypatch.setattr(mobile_route, "mobile_proof_session_to_dict", fake_to_dict)

    response = TestClient(app).get("/api/forex/mobile/proof-session/latest")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert payload["report_kind"] == "cas_forex_mobile_external_proof_session"
    assert payload["status"] == "external_proof_pending"
    assert payload["owner_token"] == "REDACTED"
    assert payload["owner_commands"]["mobile_proof_session"] == "npm --prefix ui run mobile:proof-session"
    assert payload["gates"][0]["target_url"].endswith("cas_owner_token=REDACTED")
    assert "secret-token" not in rendered


def test_mobile_verification_plan_latest_route_redacts_owner_plan(monkeypatch) -> None:
    mobile_route._mobile_evidence_cache.clear()

    monkeypatch.setattr(
        mobile_route,
        "build_mobile_verification_plan",
        lambda: {
            "report_kind": "cas_forex_mobile_verification_plan",
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external gate(s) remain.",
            "owner_token": "secret-token",
            "text": "Open http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
            "owner_commands": {"mobile_verification_plan": "npm --prefix ui run mobile:verification-plan"},
            "remaining_external_gates": ["Open Quick Start from a real phone."],
            "next_verification_actions": [
                {
                    "action_id": "phone_browser_proof",
                    "target_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
                }
            ],
        },
    )

    response = TestClient(app).get("/api/forex/mobile/verification-plan/latest")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert payload["report_kind"] == "cas_forex_mobile_verification_plan"
    assert payload["status"] == "external_proof_pending"
    assert Path(payload["default_output_paths"]["json_path"]).parts[-4:] == (
        "evidence_runs",
        "mobile_verification_plan",
        "latest",
        "mobile_verification_plan.json",
    )
    assert payload["owner_token"] == "REDACTED"
    assert payload["owner_commands"]["mobile_verification_plan"] == "npm --prefix ui run mobile:verification-plan"
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_mobile_final_verification_latest_route_redacts_owner_handoff(monkeypatch) -> None:
    mobile_route._mobile_evidence_cache.clear()

    def fake_final_to_dict(report: object) -> dict[str, Any]:  # noqa: ARG001
        return {
            "report_kind": "cas_forex_mobile_final_verification",
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 2 final external gate(s) remain.",
            "owner_token": "secret-token",
            "next_owner_step": "Open http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
            "owner_commands": {"mobile_final_verification": "npm --prefix ui run mobile:finish"},
            "gates": [
                {
                    "gate_id": "phone_browser_proof",
                    "title": "Real phone Quick Start proof",
                    "satisfied": False,
                    "target_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
                }
            ],
        }

    monkeypatch.setattr(mobile_route, "build_mobile_final_verification", lambda: SimpleNamespace(status="unused"))
    monkeypatch.setattr(mobile_route, "mobile_final_verification_to_dict", fake_final_to_dict)

    response = TestClient(app).get("/api/forex/mobile/final-verification/latest")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert payload["report_kind"] == "cas_forex_mobile_final_verification"
    assert payload["status"] == "external_proof_pending"
    assert Path(payload["default_output_paths"]["json_path"]).parts[-4:] == (
        "evidence_runs",
        "mobile_final_verification",
        "latest",
        "mobile_final_verification.json",
    )
    assert payload["owner_token"] == "REDACTED"
    assert payload["owner_commands"]["mobile_final_verification"] == "npm --prefix ui run mobile:finish"
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_mobile_final_verification_refresh_route_writes_and_redacts(monkeypatch, tmp_path: Path) -> None:
    mobile_route._mobile_evidence_cache.clear()
    calls: dict[str, Any] = {}

    def fake_final_to_dict(report: object) -> dict[str, Any]:  # noqa: ARG001
        return {
            "report_kind": "cas_forex_mobile_final_verification",
            "status": "external_proof_pending",
            "owner_token": "secret-token",
            "next_owner_step": "Open http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
            "owner_commands": {"mobile_final_verification": "npm --prefix ui run mobile:finish"},
        }

    def fake_write(report: object) -> dict[str, str]:
        calls["report"] = report
        return {
            "json_path": str(tmp_path / "mobile_final_verification.json"),
            "readme_path": str(tmp_path / "README.md"),
        }

    monkeypatch.setattr(mobile_route, "build_mobile_final_verification", lambda: SimpleNamespace(status="unused"))
    monkeypatch.setattr(mobile_route, "mobile_final_verification_to_dict", fake_final_to_dict)
    monkeypatch.setattr(mobile_route, "write_mobile_final_verification", fake_write)

    response = TestClient(app).post("/api/forex/mobile/final-verification/refresh")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert calls["report"].status == "unused"
    assert payload["written_paths"]["json_path"].endswith("mobile_final_verification.json")
    assert payload["written_paths"]["readme_path"].endswith("README.md")
    assert payload["owner_token"] == "REDACTED"
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_mobile_verification_plan_refresh_route_writes_and_redacts(monkeypatch, tmp_path: Path) -> None:
    mobile_route._mobile_evidence_cache.clear()
    calls: dict[str, Any] = {}

    def fake_plan() -> dict[str, Any]:
        return {
            "report_kind": "cas_forex_mobile_verification_plan",
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external gate(s) remain.",
            "owner_token": "secret-token",
            "text": "Open http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
            "owner_commands": {"mobile_verification_plan": "npm --prefix ui run mobile:verification-plan"},
        }

    def fake_write(plan: dict[str, Any]) -> dict[str, str]:
        calls["plan"] = plan
        return {
            "json_path": str(tmp_path / "mobile_verification_plan.json"),
            "readme_path": str(tmp_path / "README.md"),
        }

    monkeypatch.setattr(mobile_route, "build_mobile_verification_plan", fake_plan)
    monkeypatch.setattr(mobile_route, "write_mobile_verification_plan", fake_write)

    response = TestClient(app).post("/api/forex/mobile/verification-plan/refresh")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert calls["plan"]["owner_token"] == "secret-token"
    assert payload["written_paths"]["json_path"].endswith("mobile_verification_plan.json")
    assert payload["written_paths"]["readme_path"].endswith("README.md")
    assert payload["owner_token"] == "REDACTED"
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_mobile_verification_session_refresh_route_writes_and_redacts(monkeypatch, tmp_path: Path) -> None:
    mobile_route._mobile_evidence_cache.clear()
    calls: dict[str, Any] = {}

    def fake_write(report: dict[str, Any]) -> dict[str, str]:
        calls["report"] = report
        return {
            "json_path": str(tmp_path / "phone_verification_session.json"),
            "readme_path": str(tmp_path / "README.md"),
        }

    monkeypatch.setattr(mobile_route, "build_phone_verification_session", _raw_session_payload)
    monkeypatch.setattr(mobile_route, "write_phone_verification_session", fake_write)

    response = TestClient(app).post("/api/forex/mobile/verification-session/refresh")

    assert response.status_code == 200
    payload = response.json()
    rendered = json.dumps(payload)
    assert calls["report"]["owner_token"] == "secret-token"
    assert payload["written_paths"]["json_path"].endswith("phone_verification_session.json")
    assert payload["written_paths"]["readme_path"].endswith("README.md")
    assert payload["owner_token"] == "REDACTED"
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered
