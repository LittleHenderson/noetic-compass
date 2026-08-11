"""Tests for exposing latest mobile readiness evidence to the app UI."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cas_forex.mobile_readiness_latest import latest_mobile_readiness_report
from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof
from cas_forex.mobile_phone_proof import record_phone_runtime_proof


def test_latest_mobile_readiness_report_reads_stack_evidence_and_redacts_token(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["phone"],
                "checks": [
                    {
                        "check_id": "owner_pairing_payload",
                        "status": "pass",
                        "success": True,
                        "detail": "ok",
                        "evidence": {
                            "first_native_pairing_url": (
                                "casforex://pair?cas_owner_token=secret-token"
                                "&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex"
                            )
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)
    rendered = json.dumps(report)

    assert report["status"] == "LATEST_EVIDENCE_FOUND"
    assert report["web_base"] == "http://10.0.0.6:4173"
    assert report["phone_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert report["verification_commands"]["phone_proof_watcher"] == "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    assert report["verification_commands"]["phone_verification_session"] == "npm --prefix ui run mobile:verify-session"
    assert report["verification_commands"]["mobile_proof_session"] == "npm --prefix ui run mobile:proof-session"
    assert report["verification_commands"]["mobile_final_verification"] == "npm --prefix ui run mobile:finish"
    assert report["verification_commands"]["mobile_final_verification_watch_all"] == "npm --prefix ui run mobile:finish -- --watch-all"
    assert report["verification_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert report["verification_commands"]["mobile_readiness"] == "npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173"
    assert report["verification_commands"]["mobile_stack"] == "npm --prefix ui run mobile:stack -- --web-base http://10.0.0.6:4173"
    assert report["verification_commands"]["release_bundle"] == "python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --exit-code-on-failure"
    assert report["verification_commands"]["apk_release_build"] == "npm --prefix ui run mobile:apk:release"
    assert report["verification_commands"]["apk_device_list"] == "npm --prefix ui run mobile:apk:devices"
    assert report["verification_commands"]["apk_install_pair"] == "npm --prefix ui run mobile:apk:install-pair"
    assert report["verification_commands"]["apk_wait_install_pair"] == "npm --prefix ui run mobile:apk:wait-install-pair"
    assert report["verification_commands"]["docker_engine_diagnose"] == "npm --prefix ui run mobile:docker-check"
    assert report["verification_commands"]["docker_desktop_install"] == "npm --prefix ui run mobile:docker-install"
    assert report["verification_commands"]["docker_desktop_install_elevated"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert report["verification_commands"]["docker_engine_check"] == 'docker version --format "{{.Server.Version}}"'
    assert report["verification_commands"]["docker_compose_build"] == "docker compose build"
    assert report["next_verification_actions"][0]["action_id"] == "phone_browser_proof"
    assert report["next_verification_actions"][0]["target_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert report["next_verification_actions"][0]["command"] == "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    assert report["package_ready_for_phone_install"] is True
    assert report["physical_phone_verified"] is False
    assert report["android_release_signing_ready"] is False
    assert report["android_release_signing_status"] == "missing_config"
    assert report["android_release_apk_exists"] is False
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["android_release_signing"]["status"] == "external"
    assert "owner-authorized runtime gates" in report["claim_boundary"]
    assert "does not grant" not in report["claim_boundary"]
    assert "secret-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered


def test_latest_mobile_readiness_report_prefers_pairing_url_over_stale_private_web_base(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://172.16.8.129:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": True,
                "summary": "ready",
                "remaining_external_gates": ["phone"],
                "checks": [
                    {
                        "check_id": "owner_pairing_payload",
                        "status": "pass",
                        "success": True,
                        "detail": "ok",
                        "evidence": {
                            "selected_pairing_url": (
                                "http://10.202.178.108:4173/?page=quick-start"
                                "#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.202.178.108%3A4173%2Fapi%2Fforex"
                            ),
                            "selected_pairing_api_base": "http://10.202.178.108:4173/api/forex",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["web_base"] == "http://172.16.8.129:4173"
    assert report["phone_quick_start_url"] == "http://10.202.178.108:4173/?page=quick-start"
    assert report["next_verification_actions"][0]["target_url"] == "http://10.202.178.108:4173/?page=quick-start"


def test_latest_mobile_readiness_report_prefers_newer_release_evidence(tmp_path: Path) -> None:
    stack = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    release = tmp_path / "evidence_runs" / "web_phone_release" / "latest"
    stack.mkdir(parents=True)
    release.mkdir(parents=True)
    (stack / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://stale-stack.test",
                "package_ready_for_phone_install": False,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "stale stack",
                "remaining_external_gates": ["stale-stack-gate"],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    (release / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T01:00:00+00:00",
                "web_base": "http://fresh-release.test",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "fresh release",
                "remaining_external_gates": ["fresh-release-gate"],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    source_parts = Path(report["source_path"]).parts
    assert source_parts[-3:] == ("web_phone_release", "latest", "mobile_release_readiness.json")
    assert report["web_base"] == "http://fresh-release.test"
    assert report["phone_quick_start_url"] == "http://fresh-release.test/?page=quick-start"
    assert report["package_ready_for_phone_install"] is True
    assert report["remaining_external_gates"] == ["fresh-release-gate"]


def test_latest_mobile_readiness_report_flattens_docker_install_attempt(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["docker"],
                "checks": [
                    {
                        "check_id": "docker_cli",
                        "status": "external",
                        "success": False,
                        "detail": "Docker CLI not found.",
                        "evidence": {
                            "docker_desktop_install_command": "winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements",
                            "docker_desktop_install_attempt": {
                                "status": "admin_elevation_required",
                                "detail": "Docker Desktop installer was reached through winget, but installation requires administrator elevation.",
                                "returncode": 4294967291,
                                "installer_exit_code": 4294967291,
                                "generated_at": "2026-07-05T01:00:00+00:00",
                                "admin_elevation_required": True,
                            },
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["docker_engine_status"] == "external"
    assert report["docker_desktop_install_attempt_status"] == "admin_elevation_required"
    assert report["docker_desktop_install_attempt_returncode"] == 4294967291
    assert report["docker_desktop_install_attempt_installer_exit_code"] == 4294967291
    assert report["docker_desktop_install_attempt_generated_at"] == "2026-07-05T01:00:00+00:00"
    assert report["docker_desktop_install_attempt_admin_elevation_required"] is True
    assert report["docker_desktop_elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"


def test_latest_mobile_readiness_report_exposes_android_device_probe_summary(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["apk"],
                "checks": [
                    {
                        "check_id": "android_device_probe",
                        "status": "pass",
                        "success": True,
                        "detail": "1 Android device(s) ready.",
                        "evidence": {
                            "adb_path": "C:/Android/platform-tools/adb.exe",
                            "devices": [
                                {"serial": "ZY22READY", "state": "device", "detail": "product:pixel"},
                                {"serial": "ZY22BLOCKED", "state": "unauthorized", "detail": "usb:1-2"},
                            ],
                            "message": "Android device ready for install.",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["android_device_ready"] is True
    assert report["android_device_count"] == 2
    assert report["android_device_ready_count"] == 1
    assert report["android_device_status"] == "pass"
    assert report["android_device_detail"] == "1 Android device(s) ready."
    assert report["android_adb_path"] == "C:/Android/platform-tools/adb.exe"


def test_latest_mobile_readiness_report_exposes_docker_check_summary(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["docker"],
                "checks": [
                    {
                        "check_id": "docker_cli",
                        "status": "external",
                        "success": False,
                        "detail": "Docker CLI not found on PATH or standard Docker Desktop paths.",
                        "evidence": {
                            "docker_path": None,
                            "docker_server_version": None,
                            "wsl_docker": {
                                "checked": True,
                                "engine_available": False,
                                "distros": [{"name": "Ubuntu", "docker_path": None}],
                            },
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["docker_available"] is False
    assert report["docker_engine_status"] == "external"
    assert report["docker_engine_detail"] == "Docker CLI not found on PATH or standard Docker Desktop paths."
    assert report["docker_cli_path"] is None
    assert report["docker_server_version"] is None
    assert report["docker_wsl_checked"] is True
    assert report["docker_wsl_engine_available"] is False


def test_latest_mobile_readiness_report_exposes_android_release_signing(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    android = tmp_path / "ui" / "android"
    release_apk = android / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
    evidence.mkdir(parents=True)
    android.mkdir(parents=True)
    release_apk.parent.mkdir(parents=True)
    (android / "keystore.properties").write_text(
        "\n".join(
            [
                "storeFile=cas-forex-release.jks",
                "storePassword=top-secret-store",
                "keyAlias=cas-forex",
                "keyPassword=top-secret-key",
            ]
        ),
        encoding="utf-8",
    )
    (android / "cas-forex-release.jks").write_bytes(b"fake-keystore")
    release_apk.write_bytes(b"signed-apk")
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": [],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)
    rendered = json.dumps(report)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["android_release_signing_ready"] is True
    assert report["android_release_signing_status"] == "ready"
    assert report["android_release_apk_exists"] is True
    assert report["android_release_apk_sha256"]
    assert report["android_release_signing"]["input_sources"]["storePassword"] == "keystore.properties"
    assert checks["android_release_signing"]["status"] == "pass"
    assert checks["android_release_signing"]["evidence"]["release_apk_exists"] is True
    assert "top-secret" not in rendered


def test_latest_mobile_readiness_report_overlays_fresh_phone_browser_proof(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": [
                    "Open Quick Start from a real phone over the LAN preview to record verified phone browser/PWA runtime proof.",
                    "Attach an Android phone and run npm run mobile:apk:install-pair to prove APK install plus native pairing launch.",
                    "Install Docker Desktop or verify the container image on a host with Docker available.",
                ],
                "checks": [
                    {
                        "check_id": "phone_runtime_proof",
                        "status": "external",
                        "success": False,
                        "detail": "No fresh phone browser/PWA runtime proof is recorded; open Quick Start from a real phone.",
                        "evidence": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "url_origin": "http://10.0.0.6:4173",
            "display_mode": "standalone",
            "standalone_pwa": True,
            "user_agent": "Mozilla/5.0 (Linux; Android 15; Pixel) Mobile Safari/537.36",
            "platform": "Linux armv8l",
            "viewport_width": 390,
            "screen_width": 390,
            "max_touch_points": 5,
        },
        workspace_root=tmp_path,
        client_host="10.0.0.44",
        client_api_base="http://10.0.0.6:4173/api/forex",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["physical_phone_verified"] is False
    assert report["phone_browser_verified"] is True
    assert report["phone_proof_device_class"] == "phone"
    assert report["phone_proof_installed_mode"] is True
    assert report["phone_proof_fresh"] is True
    assert report["phone_proof_age_seconds"] >= 0
    assert report["phone_proof_expires_at"]
    assert report["phone_proof_max_age_hours"] == 24
    assert report["phone_proof_api_base_host"] == "10.0.0.6"
    assert report["phone_proof_api_base_network_path"] == "same_origin_proxy"
    assert report["phone_proof_api_base_source"] == "request-header"
    assert "Fresh phone browser/PWA runtime proof" in report["summary"]
    assert not any("Open Quick Start from a real phone" in gate for gate in report["remaining_external_gates"])
    assert any("mobile:apk:install-pair" in gate for gate in report["remaining_external_gates"])
    assert any("Docker" in gate for gate in report["remaining_external_gates"])
    action_ids = [action["action_id"] for action in report["next_verification_actions"]]
    assert "phone_browser_proof" not in action_ids
    assert action_ids == ["android_apk_install_pairing", "docker_engine"]
    assert report["next_verification_actions"][0]["command"] == "npm --prefix ui run mobile:apk:wait-install-pair"
    assert report["next_verification_actions"][1]["command"] == "npm --prefix ui run mobile:docker-check"
    assert "npm --prefix ui run mobile:docker-install-elevated" in report["next_verification_actions"][1]["secondary_commands"]
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["phone_runtime_proof"]["status"] == "pass"
    assert checks["phone_runtime_proof"]["success"] is True
    assert checks["phone_runtime_proof"]["evidence"]["effective_client_host"] == "10.0.0.44"
    assert checks["phone_runtime_proof"]["evidence"]["expires_at"]


def test_latest_mobile_readiness_report_exposes_stale_phone_proof_age(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["phone"],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    proof_dir = tmp_path / "evidence_runs" / "mobile_phone_proof" / "latest"
    proof_dir.mkdir(parents=True)
    stale_generated_at = datetime.now(timezone.utc) - timedelta(hours=25)
    (proof_dir / "phone_runtime_proof.json").write_text(
        json.dumps(
            {
                "report_kind": "cas_forex_phone_runtime_proof",
                "generated_at": stale_generated_at.isoformat(),
                "phone_browser_observed": True,
                "phone_browser_verified": True,
                "device_class": "phone",
                "installed_mode_detected": True,
                "effective_client_host": "10.0.0.44",
            }
        ),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["phone_browser_verified"] is False
    assert report["phone_proof_fresh"] is False
    assert report["phone_proof_age_seconds"] >= 25 * 60 * 60
    assert report["phone_proof_expires_at"]
    action_ids = [action["action_id"] for action in report["next_verification_actions"]]
    assert "phone_browser_proof" in action_ids
    assert any("Open Quick Start from a real phone" in gate for gate in report["remaining_external_gates"])


def test_latest_mobile_readiness_report_overlays_fresh_apk_install_pairing_proof(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    apk = tmp_path / "repo" / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    evidence.mkdir(parents=True)
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
                "summary": "ready",
                "remaining_external_gates": [
                    "Open Quick Start from a real phone over the LAN preview to record verified phone browser/PWA runtime proof.",
                    "Attach an Android phone and run npm run mobile:apk:install-pair to prove APK install plus native pairing launch.",
                    "Install Docker Desktop or verify the container image on a host with Docker available.",
                ],
                "checks": [
                    {
                        "check_id": "native_pairing_launch",
                        "status": "not_run",
                        "success": False,
                        "detail": "Native pairing launch was not requested.",
                        "evidence": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    record_android_apk_install_pairing_proof(
        workspace_root=tmp_path,
        install_report={
            "success": True,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "apk_path": str(apk),
            "selected_serial": "ZY22DEVICE",
            "command": ("adb", "-s", "ZY22DEVICE", "install", "-r", str(apk)),
            "message": "Debug APK installed successfully.",
        },
        native_pairing_launch={
            "success": True,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "package_id": "com.casforex.cockpit",
            "selected_serial": "ZY22DEVICE",
            "pairing_url": "casforex://pair?cas_owner_token=secret-token",
            "command": ("adb", "-s", "ZY22DEVICE", "shell", "am", "start"),
            "message": "Native pairing deep link launched successfully.",
        },
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)
    rendered = json.dumps(report)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["physical_phone_verified"] is True
    assert report["apk_install_pairing_verified"] is True
    assert report["apk_install_pairing_generated_at"]
    assert report["apk_install_pairing_selected_serial"] == "ZY22DEVICE"
    assert report["apk_install_pairing_package_id"] == "com.casforex.cockpit"
    assert report["apk_install_pairing_apk_sha256"]
    assert report["apk_install_pairing_proof"]["android_apk_install_pairing_verified"] is True
    assert "secret-token" not in rendered
    assert not any("mobile:apk:install-pair" in gate for gate in report["remaining_external_gates"])
    assert any("Open Quick Start from a real phone" in gate for gate in report["remaining_external_gates"])
    assert any("Docker" in gate for gate in report["remaining_external_gates"])
    action_ids = [action["action_id"] for action in report["next_verification_actions"]]
    assert "android_apk_install_pairing" not in action_ids
    assert action_ids == ["phone_browser_proof", "docker_engine"]
    assert checks["android_apk_install_pairing_proof"]["status"] == "pass"


def test_latest_mobile_readiness_report_exposes_failed_apk_install_pairing_attempt(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    apk = tmp_path / "repo" / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    evidence.mkdir(parents=True)
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
                "summary": "ready",
                "remaining_external_gates": [
                    "Attach an Android phone and run npm run mobile:apk:install-pair to prove APK install plus native pairing launch.",
                ],
                "checks": [],
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

    report = latest_mobile_readiness_report(workspace_root=tmp_path)
    rendered = json.dumps(report)

    assert report["physical_phone_verified"] is False
    assert report["apk_install_pairing_verified"] is False
    assert report["apk_install_pairing_proof"] is None
    assert report["apk_install_pairing_attempt_recorded"] is True
    assert report["apk_install_pairing_attempt_status"] == "install_failed"
    assert report["apk_install_pairing_attempt_fresh"] is True
    assert report["apk_install_pairing_attempt_install_success"] is False
    assert report["apk_install_pairing_attempt_native_pairing_success"] is False
    assert report["apk_install_pairing_attempt_message"] == "No ready Android device is attached."
    assert report["apk_install_pairing_attempt_age_seconds"] >= 0
    assert report["apk_install_pairing_attempt_expires_at"]
    assert "secret-token" not in rendered
    action_ids = [action["action_id"] for action in report["next_verification_actions"]]
    assert "android_apk_install_pairing" in action_ids


def test_latest_mobile_readiness_report_invalidates_apk_proof_when_apk_rebuilt(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    apk = tmp_path / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    evidence.mkdir(parents=True)
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
                "summary": "ready",
                "remaining_external_gates": [
                    "Attach an Android phone and run npm run mobile:apk:install-pair to prove APK install plus native pairing launch.",
                ],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    record_android_apk_install_pairing_proof(
        workspace_root=tmp_path,
        install_report={
            "success": True,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "apk_path": str(apk),
            "selected_serial": "ZY22DEVICE",
            "command": ("adb", "-s", "ZY22DEVICE", "install", "-r", str(apk)),
            "message": "Debug APK installed successfully.",
        },
        native_pairing_launch={
            "success": True,
            "dry_run": False,
            "adb_path": "C:/Android/adb.exe",
            "package_id": "com.casforex.cockpit",
            "selected_serial": "ZY22DEVICE",
            "pairing_url": "casforex://pair?cas_owner_token=secret-token",
            "command": ("adb", "-s", "ZY22DEVICE", "shell", "am", "start"),
            "message": "Native pairing deep link launched successfully.",
        },
    )
    apk.write_bytes(b"apk-v2")

    report = latest_mobile_readiness_report(workspace_root=tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["physical_phone_verified"] is False
    assert report["apk_install_pairing_verified"] is False
    assert report["apk_install_pairing_apk_matches_current_artifact"] is False
    assert report["apk_install_pairing_proof"]["is_fresh"] is False
    assert report["apk_install_pairing_attempt_status"] == "stale_apk"
    assert report["apk_install_pairing_attempt_apk_matches_current_artifact"] is False
    assert "different APK build" in report["apk_install_pairing_attempt_message"]
    assert checks["android_apk_install_pairing_attempt"]["status"] == "external"
    assert "different APK build" in checks["android_apk_install_pairing_attempt"]["detail"]
    action_ids = [action["action_id"] for action in report["next_verification_actions"]]
    assert "android_apk_install_pairing" in action_ids


def test_latest_mobile_readiness_report_exposes_apk_runtime_without_clearing_install_pair_gate(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": [
                    "Open Quick Start from a real phone over the LAN preview to record verified phone browser/PWA runtime proof.",
                    "Attach an Android phone and run npm run mobile:apk:install-pair to prove APK install plus native pairing launch.",
                ],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "apk",
            "url_origin": "capacitor://localhost",
            "display_mode": "standalone",
            "standalone_pwa": True,
            "user_agent": "Mozilla/5.0 (Linux; Android 15; Pixel) Mobile Safari/537.36",
            "platform": "Linux armv8l",
            "viewport_width": 390,
            "screen_width": 390,
            "max_touch_points": 5,
        },
        workspace_root=tmp_path,
        client_host="10.0.0.44",
        client_api_base="http://10.0.0.6:8765/api/forex",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["phone_browser_verified"] is True
    assert report["physical_phone_verified"] is False
    assert report["apk_runtime_status"] == "verified"
    assert report["apk_runtime_observed"] is True
    assert report["apk_runtime_verified"] is True
    assert report["apk_runtime_fresh"] is True
    assert report["apk_runtime_api_base_network_path"] == "direct_api"
    assert report["apk_runtime_local_runtime_only"] is False
    assert report["apk_install_pairing_verified"] is False
    assert any("mobile:apk:install-pair" in gate for gate in report["remaining_external_gates"])
    action_ids = [action["action_id"] for action in report["next_verification_actions"]]
    assert "phone_browser_proof" not in action_ids
    assert "android_apk_install_pairing" in action_ids
    assert checks["apk_runtime_observation"]["status"] == "pass"
    assert "ADB install/native-pairing proof is still tracked separately" in checks["apk_runtime_observation"]["detail"]


def test_latest_mobile_readiness_report_exposes_unverified_phone_observation(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["phone"],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "display_mode": "standalone",
            "standalone_pwa": True,
            "user_agent": "Mozilla/5.0 (iPhone) Mobile Safari/604.1",
            "platform": "iPhone",
            "viewport_width": 390,
            "screen_width": 390,
            "max_touch_points": 5,
        },
        workspace_root=tmp_path,
        client_host="127.0.0.1",
        client_api_base="http://127.0.0.1:8765/api/forex",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["phone_browser_observed"] is True
    assert report["phone_browser_verified"] is False
    assert report["phone_observation_device_class"] == "phone"
    assert report["phone_observation_installed_mode"] is True
    assert report["phone_observation_fresh"] is True
    assert report["phone_observation_age_seconds"] >= 0
    assert report["phone_observation_expires_at"]
    assert report["phone_observation_max_age_hours"] == 24
    assert report["phone_observation_local_runtime_only"] is True
    assert report["phone_observation_client_host_source"] == "request-client"
    assert report["phone_observation_api_base_host"] == "127.0.0.1"
    assert report["phone_observation_api_base_network_path"] == "loopback_api"
    assert report["phone_observation_api_base_source"] == "request-header"
    assert report["phone_proof"] is None
    assert "Phone-like runtime was observed" in report["summary"]
    assert any("Open Quick Start from a real phone" in gate for gate in report["remaining_external_gates"])


def test_latest_mobile_readiness_report_keeps_phone_observation_after_desktop_visit(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": True,
                "physical_phone_verified": False,
                "docker_available": False,
                "summary": "ready",
                "remaining_external_gates": ["phone"],
                "checks": [],
            }
        ),
        encoding="utf-8",
    )
    record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "display_mode": "standalone",
            "standalone_pwa": True,
            "user_agent": "Mozilla/5.0 (iPhone) Mobile Safari/604.1",
            "platform": "iPhone",
            "viewport_width": 390,
            "screen_width": 390,
            "max_touch_points": 5,
        },
        workspace_root=tmp_path,
        client_host="127.0.0.1",
    )
    record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "display_mode": "browser",
            "standalone_pwa": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "platform": "Win32",
            "viewport_width": 1280,
            "screen_width": 1920,
            "max_touch_points": 0,
        },
        workspace_root=tmp_path,
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["phone_browser_observed"] is True
    assert report["phone_browser_verified"] is False
    assert report["phone_observation_device_class"] == "phone"
    assert report["phone_observation_local_runtime_only"] is True
    assert report["phone_proof"] is None


def test_latest_mobile_readiness_report_returns_missing_packet(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["status"] == "EVIDENCE_MISSING"
    assert report["phone_quick_start_url"] is None
    assert report["verification_commands"]["mobile_readiness"] == "npm --prefix ui run mobile:readiness"
    assert report["verification_commands"]["mobile_proof_session"] == "npm --prefix ui run mobile:proof-session"
    assert report["verification_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert report["verification_commands"]["release_bundle"] == "python scripts/build_web_phone_release_bundle.py --exit-code-on-failure"
    assert report["verification_commands"]["apk_release_build"] == "npm --prefix ui run mobile:apk:release"
    assert report["verification_commands"]["apk_wait_install_pair"] == "npm --prefix ui run mobile:apk:wait-install-pair"
    assert report["verification_commands"]["docker_engine_diagnose"] == "npm --prefix ui run mobile:docker-check"
    assert report["verification_commands"]["docker_desktop_install"] == "npm --prefix ui run mobile:docker-install"
    assert report["verification_commands"]["docker_desktop_install_elevated"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert report["verification_commands"]["docker_engine_check"] == 'docker version --format "{{.Server.Version}}"'
    assert report["package_ready_for_phone_install"] is False
    assert report["android_release_signing_status"] == "missing_config"
    assert report["phone_browser_observed"] is False
    assert report["phone_browser_verified"] is False
    assert report["remaining_external_gates"]
    assert report["next_verification_actions"][0]["action_id"] == "release_bundle"
    assert report["next_verification_actions"][0]["command"] == "python scripts/build_web_phone_release_bundle.py --exit-code-on-failure"
    assert "owner-authorized runtime gates" in report["claim_boundary"]
    assert "does not change trading authority" not in report["claim_boundary"]


def test_latest_mobile_readiness_report_scope_survives_malformed_packet(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True)
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(["not", "an", "object"]),
        encoding="utf-8",
    )

    report = latest_mobile_readiness_report(workspace_root=tmp_path)

    assert report["status"] == "EVIDENCE_MALFORMED"
    assert "owner-authorized runtime gates" in report["claim_boundary"]
    assert "does not grant" not in report["claim_boundary"]
