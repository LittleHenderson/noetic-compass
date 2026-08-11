"""Tests for the owner-facing phone verification session summary."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof
from cas_forex.phone_verification_session import (
    build_phone_verification_session,
    render_phone_verification_session,
    write_phone_verification_session,
)


def test_phone_verification_session_summarizes_external_proof_gates(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    readme = tmp_path / "evidence_runs" / "web_phone_release" / "latest" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# release bundle", encoding="utf-8")
    bundle_manifest = readme.parent / "phone_release_bundle.json"
    bundle_manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "artifact_id": "android_debug_apk",
                        "path": "ui/android/app/build/outputs/apk/debug/app-debug.apk",
                        "exists": True,
                        "size_bytes": 123456,
                        "sha256": "apk-sha",
                        "copied_to": "evidence_runs/web_phone_release/latest/cas-forex-debug.apk",
                    },
                    {
                        "artifact_id": "web_index",
                        "path": "ui/dist/index.html",
                        "exists": True,
                        "size_bytes": 111,
                        "sha256": "index-sha",
                        "copied_to": None,
                    },
                    {
                        "artifact_id": "android_release_apk",
                        "path": "ui/android/app/build/outputs/apk/release/app-release.apk",
                        "exists": True,
                        "size_bytes": 654321,
                        "sha256": "release-sha",
                        "copied_to": "evidence_runs/web_phone_release/latest/cas-forex-release.apk",
                    },
                    {
                        "artifact_id": "pwa_manifest",
                        "path": "ui/dist/manifest.webmanifest",
                        "exists": True,
                        "size_bytes": 222,
                        "sha256": "manifest-sha",
                        "copied_to": None,
                    },
                    {
                        "artifact_id": "service_worker",
                        "path": "ui/dist/sw.js",
                        "exists": True,
                        "size_bytes": 333,
                        "sha256": "sw-sha",
                        "copied_to": None,
                    },
                ],
                "phone_verification_runbook": {
                    "copied_debug_apk": "evidence_runs/web_phone_release/latest/cas-forex-debug.apk",
                    "apk_install_pairing_proof_path": "evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json",
                    "verification_scope": "Phone verification proves app delivery, pairing, and network reachability.",
                    "pairing_context": {
                        "pwa_api_base": "http://10.0.0.6:4173/api/forex",
                        "direct_api_base": "http://10.0.0.6:8765/api/forex",
                        "redacted_pairing_url": "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex",
                        "redacted_native_pairing_url": "casforex://pair?cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex&page=quick-start",
                    },
                    "steps": [
                        "Open Owner Access on the PC.",
                        "Open Quick Start from the phone.",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    apk = tmp_path / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk-v1")
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "docker_engine_status": "external",
                "android_device_ready": False,
                "summary": "ready",
                "remaining_external_gates": [
                    "Open Quick Start from a real phone over the LAN preview.",
                    "Attach an Android phone and run npm --prefix ui run mobile:apk:install-pair.",
                ],
                "checks": [
                    {
                        "check_id": "android_device_probe",
                        "status": "external",
                        "success": False,
                        "detail": "No ready Android device is attached.",
                        "evidence": {
                            "adb_path": "C:/Android/platform-tools/adb.exe",
                            "devices": [],
                            "message": "No ready Android device is attached.",
                        },
                    },
                    {
                        "check_id": "docker_cli",
                        "status": "external",
                        "success": False,
                        "detail": "Docker CLI not found.",
                        "evidence": {
                            "docker_path": None,
                            "docker_desktop_install_command": "winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements",
                            "docker_desktop_install_attempt": {
                                "status": "admin_elevation_required",
                                "detail": "Docker Desktop installer was reached through winget, but installation requires administrator elevation.",
                                "returncode": 4294967291,
                                "installer_exit_code": 4294967291,
                                "generated_at": "2026-07-05T01:00:00+00:00",
                                "admin_elevation_required": True,
                            },
                            "wsl_docker": {"checked": True, "engine_available": False},
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    record_android_apk_install_pairing_proof(
        workspace_root=tmp_path,
        install_report={
            "success": False,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "apk_path": str(apk),
            "selected_serial": None,
            "command": (),
            "message": "No ready Android device is attached.",
        },
        native_pairing_launch={
            "success": False,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "package_id": "com.casforex.cockpit",
            "selected_serial": None,
            "pairing_url": "casforex://pair?cas_owner_token=secret-token",
            "command": (),
            "message": "Native pairing launch was not attempted because APK install did not succeed.",
        },
    )

    report = build_phone_verification_session(workspace_root=tmp_path)
    rendered = render_phone_verification_session(report)
    paths = write_phone_verification_session(report, workspace_root=tmp_path)
    written = json.loads(Path(paths["json_path"]).read_text(encoding="utf-8"))
    written_readme = Path(paths["readme_path"]).read_text(encoding="utf-8")
    rendered_written = render_phone_verification_session(written)

    assert report["status"] == "external_proof_pending"
    assert report["package_ready_for_phone_install"] is True
    assert report["tested_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert report["phone_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert report["release_bundle_readme"] == str(readme)
    assert report["release_bundle_manifest"] == str(bundle_manifest)
    assert report["release_artifact_summary"]["all_required_present"] is True
    assert report["release_artifact_summary"]["install_test_required_artifact_ids"] == [
        "android_debug_apk",
        "web_index",
        "pwa_manifest",
        "service_worker",
    ]
    assert report["release_artifact_summary"]["missing_required_artifacts"] == []
    assert report["release_artifact_summary"]["android_debug_apk_sha256"] == "apk-sha"
    assert report["release_artifact_summary"]["android_release_apk_present"] is True
    assert report["release_artifact_summary"]["android_release_apk_sha256"] == "release-sha"
    assert report["release_artifact_summary"]["android_release_apk_size_bytes"] == 654321
    assert report["release_artifact_summary"]["web_index_sha256"] == "index-sha"
    assert report["release_artifact_summary"]["service_worker_sha256"] == "sw-sha"
    assert report["release_artifacts"][0]["artifact_id"] == "android_debug_apk"
    assert report["pairing_context"]["pwa_api_base"] == "http://10.0.0.6:4173/api/forex"
    assert report["pairing_context"]["direct_api_base"] == "http://10.0.0.6:8765/api/forex"
    assert report["pairing_context"]["redacted_pairing_url"].endswith("cas_owner_token=REDACTED&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex")
    assert report["pairing_context"]["redacted_native_pairing_url"].startswith("casforex://pair?cas_owner_token=REDACTED")
    assert report["phone_verification_steps"] == [
        "Open Owner Access on the PC.",
        "Open Quick Start from the phone.",
    ]
    assert report["copied_debug_apk"] == "evidence_runs/web_phone_release/latest/cas-forex-debug.apk"
    assert report["apk_install_pairing_proof_path"] == "evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json"
    assert report["owner_commands"]["phone_verification_session"] == "npm --prefix ui run mobile:verify-session"
    assert report["owner_commands"]["mobile_proof_session"] == "npm --prefix ui run mobile:proof-session"
    assert report["owner_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert report["owner_commands"]["phone_proof_watcher"] == "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    assert report["owner_commands"]["apk_release_build"] == "npm --prefix ui run mobile:apk:release"
    assert report["owner_commands"]["apk_wait_install_pair"] == "npm --prefix ui run mobile:apk:wait-install-pair"
    assert report["owner_commands"]["docker_engine_diagnose"] == "npm --prefix ui run mobile:docker-check"
    assert report["owner_commands"]["docker_desktop_install"] == "npm --prefix ui run mobile:docker-install"
    assert report["owner_commands"]["docker_desktop_install_elevated"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert report["owner_commands"]["docker_compose_build"] == "docker compose build"
    assert report["next_verification_actions"][0]["target_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert report["apk_install_pairing_attempt_status"] == "install_failed"
    assert report["android_release_signing_status"] == "missing_config"
    assert report["android_device_ready"] is False
    assert report["android_adb_path"] == "C:/Android/platform-tools/adb.exe"
    assert report["docker_engine_status"] == "external"
    assert report["docker_desktop_install_attempt_status"] == "admin_elevation_required"
    assert report["docker_desktop_install_attempt_returncode"] == 4294967291
    assert report["docker_desktop_install_attempt_installer_exit_code"] == 4294967291
    assert report["proof_state"]["apk_install_pairing_attempt_status"] == "install_failed"
    assert report["proof_state"]["android_release_signing_status"] == "missing_config"
    assert report["proof_state"]["android_adb_path"] == "C:/Android/platform-tools/adb.exe"
    assert "Copy" not in rendered
    assert "## Release Artifacts" in rendered
    assert "`android_debug_apk`" in rendered
    assert "`apk-sha`" in rendered
    assert "`sw-sha`" in written_readme
    assert "## Pairing Context" in written_readme
    assert "Tested Quick Start URL" in written_readme
    assert "## Phone Verification Steps" in written_readme
    assert "Session JSON" in written_readme
    assert f"Session JSON: `{paths['json_path']}`" in rendered_written
    assert f"Session README: `{paths['readme_path']}`" in rendered_written
    assert "Docker install attempt" in written_readme
    assert "installer exit 4294967291" in written_readme
    assert "Install Docker Desktop" in written_readme
    assert "Install Docker Desktop elevated" in written_readme
    assert written["written_paths"]["json_path"] == paths["json_path"]
    assert written["written_paths"]["readme_path"] == paths["readme_path"]
    assert "Build Docker image" in rendered
    assert "Combined proof session" in rendered
    assert "npm --prefix ui run mobile:proof-session" in rendered
    assert "Build signed release APK" in rendered
    assert "Wait/install APK and launch pairing" in rendered
    assert "npm --prefix ui run mobile:apk:wait-install-pair" in rendered
    assert "npm --prefix ui run mobile:docker-check" in rendered
    assert "npm --prefix ui run mobile:docker-install-elevated" in rendered
    assert "Refresh this session" in rendered
    assert "Android release signing" in rendered
    assert "No ready Android device is attached." in rendered
    assert "Attach an Android phone" in rendered
    assert "secret-token" not in json.dumps(written)
    assert "secret-token" not in written_readme
    assert "owner-authorized runtime gates" in written_readme


def test_phone_verification_session_prefers_current_readiness_lan_url_over_stale_bundle(tmp_path: Path) -> None:
    release = tmp_path / "evidence_runs" / "web_phone_release" / "latest"
    release.mkdir(parents=True)
    (release / "phone_release_bundle.json").write_text(
        json.dumps(
            {
                "phone_quick_start_url": "http://192.168.137.1:4173/?page=quick-start",
                "phone_verification_runbook": {
                    "phone_quick_start_url": "http://192.168.137.1:4173/?page=quick-start",
                    "pairing_context": {
                        "pwa_api_base": "http://192.168.137.1:4173/api/forex",
                        "redacted_pairing_url": (
                            "http://192.168.137.1:4173/?page=quick-start"
                            "#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F192.168.137.1%3A4173%2Fapi%2Fforex"
                        ),
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-06T00:00:00+00:00",
                "web_base": "http://172.16.8.129:4173",
                "phone_quick_start_url": "http://192.168.137.1:4173/?page=quick-start",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": [
                    "Open Quick Start from a real phone over the LAN preview.",
                ],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    report = build_phone_verification_session(workspace_root=tmp_path)

    assert report["phone_quick_start_url"] == "http://172.16.8.129:4173/?page=quick-start"
    assert report["next_verification_actions"][0]["target_url"] == "http://172.16.8.129:4173/?page=quick-start"
