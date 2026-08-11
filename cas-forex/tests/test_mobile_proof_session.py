"""Tests for the combined owner-facing mobile proof session."""

from __future__ import annotations

import json
from pathlib import Path

from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof
from cas_forex.mobile_phone_proof import record_phone_runtime_proof
from cas_forex.mobile_phone_verifier import PhoneProofWatchStatus
from cas_forex.mobile_proof_session import (
    REPORT_KIND,
    build_mobile_proof_session,
    mobile_proof_session_to_dict,
    mobile_proof_session_to_json,
    render_mobile_proof_session,
)


def _write_readiness(
    root: Path,
    *,
    package_ready: bool = True,
    physical_phone_verified: bool = False,
    docker_available: bool = False,
    remaining_external_gates: list[str] | None = None,
) -> None:
    evidence = root / "evidence_runs" / "mobile_stack" / "latest"
    evidence.mkdir(parents=True, exist_ok=True)
    docker_check = {
        "check_id": "docker_cli",
        "status": "pass" if docker_available else "external",
        "success": docker_available,
        "detail": "Docker Engine answered." if docker_available else "Docker CLI not found on PATH.",
        "evidence": {
            "docker_path": "C:/Docker/docker.exe" if docker_available else None,
            "docker_server_version": "28.1.1" if docker_available else None,
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
    }
    (evidence / "mobile_release_readiness.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-05T00:00:00+00:00",
                "web_base": "http://10.0.0.6:4173",
                "package_ready_for_phone_install": package_ready,
                "physical_phone_verified": physical_phone_verified,
                "paired_api_bases_reachable": package_ready,
                "paired_api_bases_status": "pass" if package_ready else "fail",
                "paired_api_bases_detail": (
                    "paired PWA/proxy and APK/direct API bases answered with owner token"
                    if package_ready
                    else "paired API bases were not verified"
                ),
                "docker_available": docker_available,
                "summary": "ready" if package_ready else "not ready",
                "remaining_external_gates": remaining_external_gates
                if remaining_external_gates is not None
                else [
                    "Open Quick Start from a real phone over the LAN preview.",
                    "Attach an Android phone and run npm --prefix ui run mobile:apk:wait-install-pair.",
                    "Install Docker Desktop or verify Docker Engine.",
                ],
                "checks": [docker_check],
            }
        ),
        encoding="utf-8",
    )

    release = root / "evidence_runs" / "web_phone_release" / "latest"
    release.mkdir(parents=True, exist_ok=True)
    (release / "phone_release_bundle.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "artifact_id": "android_debug_apk",
                        "exists": True,
                        "size_bytes": 1234,
                        "sha256": "debug-sha",
                    },
                    {
                        "artifact_id": "android_release_apk",
                        "exists": True,
                        "size_bytes": 987,
                        "sha256": "release-sha",
                    },
                    {
                        "artifact_id": "web_index",
                        "exists": True,
                        "size_bytes": 111,
                        "sha256": "web-sha",
                    },
                    {
                        "artifact_id": "service_worker",
                        "exists": True,
                        "size_bytes": 222,
                        "sha256": "sw-sha",
                    },
                ],
                "phone_verification_runbook": {
                    "pairing_context": {
                        "pwa_api_base": "http://10.0.0.6:4173/api/forex",
                        "direct_api_base": "http://10.0.0.6:8765/api/forex",
                        "redacted_pairing_url": (
                            "http://10.0.0.6:4173/?page=quick-start"
                            "#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex"
                        ),
                        "redacted_native_pairing_url": (
                            "casforex://pair?cas_owner_token=secret-token"
                            "&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex"
                        ),
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _watch_status(*, verified: bool, observed: bool | None = None) -> PhoneProofWatchStatus:
    observed = verified if observed is None else observed
    return PhoneProofWatchStatus(
        status="VERIFIED" if verified else "MISSING",
        phone_browser_verified=verified,
        phone_browser_observed=observed,
        phone_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        tested_quick_start_url="http://127.0.0.1:4173/?page=quick-start",
        phone_proof_watcher_command="npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
        mobile_readiness_command="npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173",
        active_evidence_kind="verified_phone_proof" if verified else "none",
        installed_mode_detected=verified,
        effective_client_host="10.0.0.44" if verified else None,
        client_host_source="x-forwarded-for" if verified else None,
        generated_at="2026-07-05T00:00:00+00:00" if verified else None,
        phone_proof_fresh=verified,
        phone_proof_age_seconds=0 if verified else None,
        phone_proof_expires_at="2026-07-06T00:00:00+00:00" if verified else None,
        phone_observation_fresh=observed,
        phone_observation_age_seconds=0 if observed else None,
        phone_observation_expires_at="2026-07-06T00:00:00+00:00" if observed else None,
        readiness_source_path=None,
        summary="verified" if verified else "missing",
        next_steps=(),
    )


def test_mobile_proof_session_summarizes_pending_external_gates(tmp_path: Path) -> None:
    _write_readiness(tmp_path)

    session = build_mobile_proof_session(workspace_root=tmp_path)
    payload = mobile_proof_session_to_dict(session)
    rendered = render_mobile_proof_session(session)

    assert payload["report_kind"] == REPORT_KIND
    assert payload["status"] == "external_proof_pending"
    assert payload["package_ready_for_phone_install"] is True
    assert payload["phone_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert payload["phone_proof_target_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert payload["phone_proof_target_kind"] == "quick_start_with_live_pairing_if_needed"
    assert payload["pairing_context"]["pwa_api_base"] == "http://10.0.0.6:4173/api/forex"
    assert payload["pairing_context"]["redacted_pairing_url"].endswith("cas_owner_token=REDACTED&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex")
    assert "copyable pairing QR/link" in payload["phone_pairing_handoff"]
    assert payload["paired_api_bases_reachable"] is True
    assert payload["paired_api_bases_status"] == "pass"
    assert "owner token" in payload["paired_api_bases_detail"]
    assert payload["owner_commands"]["mobile_proof_session"] == "npm --prefix ui run mobile:proof-session"
    assert payload["owner_commands"]["docker_desktop_install"] == "npm --prefix ui run mobile:docker-install"
    assert payload["owner_commands"]["docker_desktop_install_elevated"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert payload["proof_state"]["docker_engine_status"] == "external"
    assert payload["docker_desktop_elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert payload["docker_desktop_install_attempt_status"] == "admin_elevation_required"
    assert payload["docker_desktop_install_attempt_installer_exit_code"] == 4294967291
    assert payload["release_artifact_summary"]["android_debug_apk_sha256"] == "debug-sha"
    assert payload["release_artifact_summary"]["android_release_apk_sha256"] == "release-sha"
    assert payload["release_artifact_summary"]["web_index_sha256"] == "web-sha"
    assert payload["release_artifact_summary"]["service_worker_sha256"] == "sw-sha"
    assert [gate["gate_id"] for gate in payload["gates"]] == [
        "phone_browser_proof",
        "android_apk_install_pairing",
        "docker_engine",
    ]
    assert payload["gates"][2]["command"] == "npm --prefix ui run mobile:docker-check"
    assert list(payload["remaining_external_gates"]) == [
        "Real phone Quick Start proof",
        "Android APK install and native pairing proof",
        "Docker Engine proof",
    ]
    assert "CAS Forex mobile external proof session" in rendered
    assert payload["owner_commands"]["mobile_final_verification_watch_all"] == "npm --prefix ui run mobile:finish -- --watch-all"
    assert payload["owner_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert "Watch all final gates: npm --prefix ui run mobile:finish -- --watch-all" in rendered
    assert "Watch all final gates with live links: npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links" in rendered
    assert "Proof session: npm --prefix ui run mobile:proof-session" in rendered
    assert "Debug APK: 1234 bytes, sha256=debug-sha" in rendered
    assert "Release APK: 987 bytes, sha256=release-sha" in rendered
    assert "Web index: web-sha" in rendered
    assert "Service worker: sw-sha" in rendered
    assert "Phone proof target: http://10.0.0.6:4173/?page=quick-start (quick_start_with_live_pairing_if_needed)" in rendered
    assert "Paired API bases: paired PWA/proxy and APK/direct API bases answered with owner token" in rendered
    assert "Pairing Handoff:" in rendered
    assert "saved proof-session pairing URLs are redacted by design" in rendered
    assert "will not pair a fresh phone if copied directly" in rendered
    assert "APK build-all: npm --prefix ui run mobile:apk:build-all" in rendered
    assert "APK wait/install-pair: npm --prefix ui run mobile:apk:wait-install-pair" in rendered
    assert "Docker diagnosis: npm --prefix ui run mobile:docker-check" in rendered
    assert "Docker install: npm --prefix ui run mobile:docker-install" in rendered
    assert "Docker elevated install: npm --prefix ui run mobile:docker-install-elevated" in rendered
    assert "Docker install attempt: admin_elevation_required" in rendered
    assert "installer exit 4294967291" in rendered
    assert "Copy" not in rendered
    assert "secret-token" not in rendered
    assert "secret-token" not in mobile_proof_session_to_json(session)


def test_mobile_proof_session_watch_phone_can_satisfy_phone_gate(tmp_path: Path) -> None:
    _write_readiness(tmp_path)

    session = build_mobile_proof_session(
        workspace_root=tmp_path,
        watch_phone=True,
        status_reader=lambda: _watch_status(verified=True),
        timeout_seconds=0,
    )

    assert session.status == "external_proof_pending"
    assert session.phone_browser_verified is True
    assert session.gates[0].satisfied is True
    assert [gate.title for gate in session.gates if not gate.satisfied] == [
        "Android APK install and native pairing proof",
        "Docker Engine proof",
    ]


def test_mobile_proof_session_reports_verified_when_all_external_gates_are_green(tmp_path: Path) -> None:
    apk = tmp_path / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"apk-v1")
    _write_readiness(
        tmp_path,
        physical_phone_verified=True,
        docker_available=True,
        remaining_external_gates=[],
    )
    record_phone_runtime_proof(
        {
            "source": "quick-start",
            "app_surface": "pwa",
            "display_mode": "standalone",
            "standalone_pwa": True,
            "user_agent": "Mozilla/5.0 (Linux; Android 15; Pixel) Mobile Safari/537.36",
            "platform": "Linux armv8l",
            "viewport_width": 390,
            "screen_width": 390,
            "max_touch_points": 5,
        },
        workspace_root=tmp_path,
        client_host="127.0.0.1",
        forwarded_for="10.0.0.44",
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

    session = build_mobile_proof_session(workspace_root=tmp_path)

    assert session.status == "verified"
    assert session.remaining_external_gates == ()
    assert all(gate.satisfied for gate in session.gates)
    assert "secret-token" not in mobile_proof_session_to_json(session)
