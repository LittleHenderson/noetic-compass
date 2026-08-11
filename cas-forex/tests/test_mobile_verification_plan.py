from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import cas_forex.mobile_verification_plan as plan_module


def test_mobile_verification_plan_renders_shared_redacted_owner_checklist(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        plan_module,
        "latest_mobile_readiness_report",
        lambda workspace_root=".": {
            "status": "external_proof_pending",
            "summary": "Phone package is ready; 3 external gate(s) remain.",
            "source_path": str(tmp_path / "mobile_release_readiness.json"),
            "package_ready_for_phone_install": True,
            "phone_browser_verified": False,
            "physical_phone_verified": False,
            "apk_install_pairing_verified": False,
            "apk_install_pairing_attempt_status": "install_failed",
            "docker_available": False,
            "docker_engine_status": "external",
            "docker_desktop_install_attempt_status": "admin_elevation_required",
            "phone_quick_start_url": "http://10.0.0.6:4173/?page=quick-start",
            "remaining_external_gates": ["Open Quick Start from a real phone."],
            "next_verification_actions": [
                {
                    "action_id": "phone_browser_proof",
                    "title": "Verify real phone Quick Start",
                    "target_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
                    "command": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                    "secondary_commands": ["npm --prefix ui run mobile:docker-install-elevated"],
                }
            ],
            "verification_commands": {
                "mobile_readiness": "npm --prefix ui run mobile:readiness",
                "docker_desktop_install_elevated": "npm --prefix ui run mobile:docker-install-elevated",
            },
        },
    )
    monkeypatch.setattr(plan_module, "build_mobile_proof_session", lambda workspace_root=".": SimpleNamespace())
    monkeypatch.setattr(
        plan_module,
        "mobile_proof_session_to_dict",
        lambda session: {  # noqa: ARG005
            "summary": "Phone package is ready; 3 external proof gate(s) remain.",
            "phone_proof_target_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
            "owner_commands": {"mobile_proof_session": "npm --prefix ui run mobile:proof-session"},
        },
    )
    monkeypatch.setattr(
        plan_module,
        "build_phone_verification_session",
        lambda workspace_root=".": {
            "source_path": str(tmp_path / "phone_verification_session.json"),
            "owner_token": "secret-token",
            "remaining_external_gates": ["Open Quick Start from a real phone."],
        },
    )

    plan = plan_module.build_mobile_verification_plan(workspace_root=tmp_path)
    rendered = json.dumps(plan)

    assert plan["report_kind"] == "cas_forex_mobile_verification_plan"
    assert plan["package_ready_for_phone_install"] is True
    assert plan["docker_desktop_install_attempt_status"] == "admin_elevation_required"
    assert plan["owner_commands"]["mobile_verification_plan"] == "npm --prefix ui run mobile:verification-plan"
    assert plan["owner_commands"]["mobile_final_verification_watch_all"] == "npm --prefix ui run mobile:finish -- --watch-all"
    assert plan["owner_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert "CAS Forex mobile/web verification plan" in plan["text"]
    assert "Watch all final gates: npm --prefix ui run mobile:finish -- --watch-all" in plan["text"]
    assert "Watch all final gates with live links: npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links" in plan["text"]
    assert "Docker elevated install: npm --prefix ui run mobile:docker-install-elevated" in plan["text"]
    assert "Secondary commands:" in plan["text"]
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered

    paths = plan_module.write_mobile_verification_plan(plan, workspace_root=tmp_path)
    json_path = Path(paths["json_path"])
    readme_path = Path(paths["readme_path"])
    assert json_path.parts[-4:] == ("evidence_runs", "mobile_verification_plan", "latest", "mobile_verification_plan.json")
    assert readme_path.parts[-4:] == ("evidence_runs", "mobile_verification_plan", "latest", "README.md")
    saved_json = json_path.read_text(encoding="utf-8")
    saved_readme = readme_path.read_text(encoding="utf-8")
    assert "CAS Forex mobile/web verification plan" in saved_readme
    assert "mobile_verification_plan.json" in saved_json
    assert "secret-token" not in saved_json
    assert "secret-token" not in saved_readme
