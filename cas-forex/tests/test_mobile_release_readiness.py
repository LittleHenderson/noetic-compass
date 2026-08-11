"""Tests for consolidated CAS Forex mobile release readiness reporting."""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path
from typing import Mapping

from cas_forex import mobile_release_readiness as readiness_module
from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof
from cas_forex.mobile_release_readiness import readiness_to_dict, run_mobile_release_readiness
from cas_forex.mobile_phone_proof import record_phone_runtime_proof
from cas_forex.web_phone_smoke import HttpSmokeResponse


def _response(body: str | dict, status_code: int = 200) -> HttpSmokeResponse:
    if isinstance(body, dict):
        body = json.dumps(body)
    return HttpSmokeResponse(status_code=status_code, body=body.encode("utf-8"), headers={})


def _ok_transport(
    method: str,
    url: str,
    timeout_seconds: float,
    headers: Mapping[str, str] | None = None,
) -> HttpSmokeResponse:  # noqa: ARG001
    if url.endswith("/manifest.webmanifest"):
        return _response(
            {
                "name": "CAS Forex",
                "start_url": "/?source=pwa",
                "display": "standalone",
                "icons": [
                    {"src": "/icons/cas-forex-192.png", "sizes": "192x192"},
                    {"src": "/icons/cas-forex-512.png", "sizes": "512x512"},
                ],
            }
        )
    if url.endswith("/sw.js"):
        return _response("precacheAndRoute([]); new NavigationRoute(null,{denylist:[/^\\/api\\//]});")
    if url.endswith("/api/forex/health"):
        return _response({"status": "healthy", "version": "0.1.0"})
    if url.endswith("/api/forex/owner-auth/pairing"):
        token = "secret-owner-token"
        return _response(
            {
                "report_kind": "cas_forex_owner_auth",
                "owner_token": token,
                "pairing_urls": [
                    f"http://10.0.0.6:4173/?page=quick-start#cas_owner_token={token}&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex"
                ],
                "native_pairing_urls": [
                    f"casforex://pair?cas_owner_token={token}&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex&page=quick-start"
                ],
                "pairing_api_bases": ["http://10.0.0.6:4173/api/forex"],
                "direct_api_bases": ["http://10.0.0.6:8765/api/forex"],
            }
        )
    if method.upper() == "POST" and url.endswith("/api/forex/mobile/phone-proof"):
        return _response(
            {
                "status": "DRY_RUN_NOT_RECORDED",
                "dry_run": True,
                "phone_browser_verified": True,
                "device_class": "android",
                "effective_client_host": "10.0.0.55",
                "client_host_source": "x-forwarded-for",
                "local_runtime_only": False,
                "api_base_network_path": "same_origin_proxy",
                "source_path": None,
            }
        )
    if url.endswith("/api/forex/mobile/proof-session/latest"):
        if not headers or headers.get("X-CAS-Owner-Token") != "secret-owner-token":
            return _response({"detail": "owner token required"}, status_code=401)
        return _response(
            {
                "report_kind": "cas_forex_mobile_external_proof_session",
                "status": "external_proof_pending",
                "package_ready_for_phone_install": True,
            }
        )
    return _response('<html><head><link rel="manifest" href="/manifest.webmanifest"></head><body><div id="root"></div></body></html>')


def _write_dist_and_apk(root: Path, apk: Path) -> None:
    dist = root / "ui" / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    apk.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(apk, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in ("index.html", "manifest.webmanifest", "sw.js"):
            archive.writestr(f"assets/public/{name}", (dist / name).read_bytes())
        archive.writestr("assets/padding.bin", b"0" * 1_200_000)


def test_mobile_release_readiness_marks_package_ready_and_redacts_pairing_token(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    rendered = json.dumps(payload)

    assert report.package_ready_for_phone_install is True
    assert report.physical_phone_verified is False
    assert report.phone_quick_start_url == "http://10.0.0.6:4173/?page=quick-start"
    assert payload["verification_commands"]["phone_proof_watcher"] == (
        "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    )
    assert payload["verification_commands"]["phone_verification_session"] == "npm --prefix ui run mobile:verify-session"
    assert payload["verification_commands"]["mobile_proof_session"] == "npm --prefix ui run mobile:proof-session"
    assert payload["verification_commands"]["mobile_final_verification"] == "npm --prefix ui run mobile:finish"
    assert payload["verification_commands"]["mobile_final_verification_watch_all"] == "npm --prefix ui run mobile:finish -- --watch-all"
    assert payload["verification_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert payload["verification_commands"]["mobile_readiness"] == (
        "npm --prefix ui run mobile:readiness -- --web-base http://phone-preview.test"
    )
    assert payload["verification_commands"]["mobile_stack"] == (
        "npm --prefix ui run mobile:stack -- --web-base http://phone-preview.test"
    )
    assert payload["verification_commands"]["release_bundle"] == (
        "python scripts/build_web_phone_release_bundle.py --web-base http://phone-preview.test --exit-code-on-failure"
    )
    assert payload["verification_commands"]["apk_device_list"] == "npm --prefix ui run mobile:apk:devices"
    assert payload["verification_commands"]["apk_release_build"] == "npm --prefix ui run mobile:apk:release"
    assert payload["verification_commands"]["apk_install_pair"] == "npm --prefix ui run mobile:apk:install-pair"
    assert payload["verification_commands"]["apk_wait_install_pair"] == "npm --prefix ui run mobile:apk:wait-install-pair"
    assert payload["verification_commands"]["docker_engine_diagnose"] == "npm --prefix ui run mobile:docker-check"
    assert payload["verification_commands"]["docker_desktop_install"] == "npm --prefix ui run mobile:docker-install"
    assert payload["verification_commands"]["docker_desktop_install_elevated"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert payload["verification_commands"]["docker_engine_check"] == 'docker version --format "{{.Server.Version}}"'
    assert payload["verification_commands"]["docker_compose_build"] == "docker compose build"
    assert payload["next_verification_actions"][0]["action_id"] == "phone_browser_proof"
    assert payload["next_verification_actions"][0]["target_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert payload["next_verification_actions"][0]["command"] == "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing"
    assert report.phone_browser_observed is False
    assert report.phone_browser_verified is False
    assert payload["phone_proof_fresh"] is False
    assert payload["phone_observation_fresh"] is False
    assert payload["android_release_signing_ready"] is False
    assert payload["android_release_signing_status"] == "missing_config"
    assert payload["android_release_apk_exists"] is False
    assert payload["android_release_apk_sha256"] is None
    assert payload["apk_install_pairing_attempt_status"] == "none"
    assert payload["apk_install_pairing_attempt_recorded"] is False
    assert payload["docker_engine_status"] == "not_run"
    assert payload["docker_engine_detail"] == "Docker Engine check was skipped."
    assert payload["docker_desktop_elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert payload["paired_api_bases_reachable"] is True
    assert payload["paired_api_bases_status"] == "pass"
    assert payload["paired_api_bases_detail"] == "paired PWA/proxy and APK/direct API bases answered with owner token"
    assert "secret-owner-token" not in rendered
    assert "cas_owner_token=REDACTED" in rendered
    assert "Open Quick Start from a real phone" in payload["remaining_external_gates"][0]
    checks = {check["check_id"]: check for check in payload["checks"]}
    assert checks["web_phone_smoke"]["success"] is True
    assert checks["owner_pairing_payload"]["success"] is True
    assert checks["paired_api_bases"]["success"] is True
    assert {item["kind"] for item in checks["paired_api_bases"]["evidence"]["results"]} == {"pwa_proxy", "direct_api"}
    assert checks["android_release_signing"]["status"] == "external"
    assert checks["android_release_signing"]["evidence"]["ready"] is False
    assert checks["native_pairing_launch"]["status"] == "not_run"


def test_mobile_release_readiness_fails_package_when_pairing_payload_is_malformed(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)

    def bad_pairing_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: Mapping[str, str] | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/owner-auth/pairing"):
            return _response({"report_kind": "cas_forex_owner_auth", "pairing_urls": []})
        return _ok_transport(method, url, timeout_seconds, headers)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=bad_pairing_transport,
        check_android_device=False,
        check_docker=False,
    )

    assert report.package_ready_for_phone_install is False
    checks = {check.check_id: check for check in report.checks}
    assert checks["web_phone_smoke"].success is True
    assert checks["owner_pairing_payload"].success is False
    assert checks["paired_api_bases"].success is False
    assert "web pairing URL" in checks["owner_pairing_payload"].detail


def test_mobile_release_readiness_fails_package_when_paired_api_base_is_unreachable(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)

    def broken_paired_api_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: Mapping[str, str] | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/mobile/proof-session/latest"):
            return _response({"detail": "offline"}, status_code=503)
        return _ok_transport(method, url, timeout_seconds, headers)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=broken_paired_api_transport,
        check_android_device=False,
        check_docker=False,
    )
    checks = {check.check_id: check for check in report.checks}

    assert report.package_ready_for_phone_install is False
    assert checks["web_phone_smoke"].success is True
    assert checks["owner_pairing_payload"].success is True
    assert checks["paired_api_bases"].success is False
    assert "returned HTTP 503" in checks["paired_api_bases"].detail


def test_mobile_release_readiness_retries_transient_pairing_and_paired_api_timeouts(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
    pairing_attempts = 0
    proof_attempts: dict[str, int] = {}

    def flaky_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: Mapping[str, str] | None = None,
    ) -> HttpSmokeResponse:
        nonlocal pairing_attempts
        if url.endswith("/api/forex/owner-auth/pairing"):
            pairing_attempts += 1
            if pairing_attempts in {1, 3}:
                raise TimeoutError("first owner-pairing probe stalled")
        if url.endswith("/api/forex/mobile/proof-session/latest"):
            proof_attempts[url] = proof_attempts.get(url, 0) + 1
            if "4173" in url and proof_attempts[url] == 1:
                raise TimeoutError("first PWA proof-session probe stalled")
        return _ok_transport(method, url, timeout_seconds, headers)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=flaky_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    checks = {check["check_id"]: check for check in payload["checks"]}
    paired_results = checks["paired_api_bases"]["evidence"]["results"]

    assert report.package_ready_for_phone_install is True
    assert checks["owner_pairing_payload"]["success"] is True
    assert checks["owner_pairing_payload"]["attempts"] == 2
    assert checks["paired_api_bases"]["success"] is True
    assert checks["paired_api_bases"]["attempts"] > 1
    assert any(result["kind"] == "pwa_proxy" and result["attempts"] == 2 for result in paired_results)


def test_mobile_release_readiness_falls_back_to_loopback_pairing_payload(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
    pairing_urls: list[str] = []

    def remote_pairing_is_forbidden(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: Mapping[str, str] | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/owner-auth/pairing"):
            pairing_urls.append(url)
            if url.startswith("http://127.0.0.1:8765/"):
                return _ok_transport(method, url, timeout_seconds, headers)
            return _response({"detail": "owner token required"}, status_code=401)
        return _ok_transport(method, url, timeout_seconds, headers)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://10.0.0.6:4173",
        apk_path=apk,
        transport=remote_pairing_is_forbidden,
        check_android_device=False,
        check_docker=False,
    )
    checks = {check.check_id: check for check in report.checks}

    assert report.package_ready_for_phone_install is True
    assert checks["owner_pairing_payload"].success is True
    assert "http://10.0.0.6:4173/api/forex/owner-auth/pairing" in pairing_urls
    assert "http://127.0.0.1:8765/api/forex/owner-auth/pairing" in pairing_urls


def test_mobile_release_readiness_prefers_current_pairing_url_over_unmatched_private_lan_web_base(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://172.16.8.129:4173",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )

    assert report.package_ready_for_phone_install is True
    assert report.phone_quick_start_url == "http://10.0.0.6:4173/?page=quick-start"


def test_mobile_release_readiness_selects_pairing_values_for_tested_lan_host(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)

    def multi_adapter_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: Mapping[str, str] | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/owner-auth/pairing"):
            token = "secret-owner-token"
            return _response(
                {
                    "report_kind": "cas_forex_owner_auth",
                    "owner_token": token,
                    "pairing_urls": [
                        f"http://192.168.137.1:4173/?page=quick-start#cas_owner_token={token}&cas_api_base=http%3A%2F%2F192.168.137.1%3A4173%2Fapi%2Fforex",
                        f"http://172.16.8.129:4173/?page=quick-start#cas_owner_token={token}&cas_api_base=http%3A%2F%2F172.16.8.129%3A4173%2Fapi%2Fforex",
                    ],
                    "native_pairing_urls": [
                        f"casforex://pair?cas_owner_token={token}&cas_api_base=http%3A%2F%2F192.168.137.1%3A8765%2Fapi%2Fforex&page=quick-start",
                        f"casforex://pair?cas_owner_token={token}&cas_api_base=http%3A%2F%2F172.16.8.129%3A8765%2Fapi%2Fforex&page=quick-start",
                    ],
                    "pairing_api_bases": [
                        "http://192.168.137.1:4173/api/forex",
                        "http://172.16.8.129:4173/api/forex",
                    ],
                    "direct_api_bases": [
                        "http://192.168.137.1:8765/api/forex",
                        "http://172.16.8.129:8765/api/forex",
                    ],
                }
            )
        return _ok_transport(method, url, timeout_seconds, headers)

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://172.16.8.129:4173",
        apk_path=apk,
        transport=multi_adapter_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    pairing = {check["check_id"]: check for check in payload["checks"]}["owner_pairing_payload"]["evidence"]

    assert report.package_ready_for_phone_install is True
    assert report.phone_quick_start_url == "http://172.16.8.129:4173/?page=quick-start"
    assert pairing["first_pairing_api_base"] == "http://192.168.137.1:4173/api/forex"
    assert pairing["selected_pairing_api_base"] == "http://172.16.8.129:4173/api/forex"
    assert pairing["selected_direct_api_base"] == "http://172.16.8.129:8765/api/forex"
    assert pairing["selected_pairing_url"].startswith("http://172.16.8.129:4173/")
    assert pairing["selected_native_pairing_url"].startswith("casforex://pair?")
    assert "172.16.8.129%3A8765" in pairing["selected_native_pairing_url"]


def test_mobile_release_readiness_exposes_unverified_phone_observation(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
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

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    phone_check = {check["check_id"]: check for check in payload["checks"]}["phone_runtime_proof"]

    assert report.phone_browser_observed is True
    assert report.phone_browser_verified is False
    assert payload["phone_observation_fresh"] is True
    assert payload["phone_observation_age_seconds"] >= 0
    assert payload["phone_observation_expires_at"]
    assert payload["phone_observation"]["device_class"] == "phone"
    assert payload["phone_observation"]["local_runtime_only"] is True
    assert payload["phone_proof"] is None
    assert phone_check["status"] == "external"
    assert "verified phone network proof is missing" in phone_check["detail"]
    assert "non-localhost phone browser/PWA runtime proof" in payload["remaining_external_gates"][0]


def test_mobile_release_readiness_exposes_verified_phone_proof(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
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
        forwarded_for="10.0.0.55",
    )

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    phone_check = {check["check_id"]: check for check in payload["checks"]}["phone_runtime_proof"]

    assert report.phone_browser_observed is True
    assert report.phone_browser_verified is True
    assert payload["phone_proof_fresh"] is True
    assert payload["phone_proof_age_seconds"] >= 0
    assert payload["phone_proof_expires_at"]
    assert payload["phone_proof"]["effective_client_host"] == "10.0.0.55"
    assert phone_check["status"] == "pass"
    assert not any("Open Quick Start from a real phone" in gate for gate in payload["remaining_external_gates"])


def test_mobile_release_readiness_exposes_apk_runtime_without_physical_phone_proof(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
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
        client_host="10.0.0.55",
        client_api_base="http://10.0.0.6:8765/api/forex",
    )

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    checks = {check["check_id"]: check for check in payload["checks"]}

    assert report.phone_browser_verified is True
    assert report.physical_phone_verified is False
    assert payload["apk_runtime_observed"] is True
    assert payload["apk_runtime_verified"] is True
    assert payload["apk_runtime_fresh"] is True
    assert checks["apk_runtime_observation"]["status"] == "pass"
    assert "ADB install/native-pairing proof is still tracked separately" in checks["apk_runtime_observation"]["detail"]
    assert any("mobile:apk:wait-install-pair" in gate for gate in payload["remaining_external_gates"])


def test_mobile_release_readiness_uses_persisted_apk_install_pairing_proof(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
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

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    checks = {check["check_id"]: check for check in payload["checks"]}
    rendered = json.dumps(payload)

    assert report.physical_phone_verified is True
    assert payload["apk_install_pairing_proof"]["android_apk_install_pairing_verified"] is True
    assert checks["android_apk_install_pairing_proof"]["status"] == "pass"
    assert not any("mobile:apk:wait-install-pair" in gate for gate in payload["remaining_external_gates"])
    assert "secret-token" not in rendered


def test_mobile_release_readiness_exposes_failed_apk_install_pairing_attempt(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
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

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    checks = {check["check_id"]: check for check in payload["checks"]}
    rendered = json.dumps(payload)

    assert report.physical_phone_verified is False
    assert payload["apk_install_pairing_proof"] is None
    assert payload["apk_install_pairing_attempt"]["install_success"] is False
    assert payload["apk_install_pairing_attempt_recorded"] is True
    assert payload["apk_install_pairing_attempt_status"] == "install_failed"
    assert payload["apk_install_pairing_attempt_message"] == "No ready Android device is attached."
    assert payload["apk_install_pairing_attempt_install_success"] is False
    assert payload["apk_install_pairing_attempt_native_pairing_success"] is False
    assert payload["apk_install_pairing_attempt_apk_matches_current_artifact"] is True
    assert checks["android_apk_install_pairing_attempt"]["status"] == "external"
    assert checks["android_apk_install_pairing_attempt"]["detail"] == "No ready Android device is attached."
    assert any("mobile:apk:wait-install-pair" in gate for gate in payload["remaining_external_gates"])
    assert "secret-token" not in rendered


def test_mobile_release_readiness_invalidates_apk_proof_when_apk_rebuilt(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_dist_and_apk(tmp_path, apk)
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
    apk.write_bytes(b"rebuilt-apk-v2")

    report = run_mobile_release_readiness(
        workspace_root=tmp_path,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
        check_android_device=False,
        check_docker=False,
    )
    payload = readiness_to_dict(report)
    checks = {check["check_id"]: check for check in payload["checks"]}

    assert report.physical_phone_verified is False
    assert payload["apk_install_pairing_proof"]["android_apk_install_pairing_verified"] is True
    assert payload["apk_install_pairing_verified"] is False
    assert payload["apk_install_pairing_apk_matches_current_artifact"] is False
    assert payload["apk_install_pairing_proof"]["is_fresh"] is False
    assert payload["apk_install_pairing_proof"]["apk_matches_current_artifact"] is False
    assert payload["apk_install_pairing_attempt"]["apk_matches_current_artifact"] is False
    assert payload["apk_install_pairing_attempt_status"] == "stale_apk"
    assert "different APK build" in payload["apk_install_pairing_attempt_message"]
    assert checks["android_apk_install_pairing_attempt"]["status"] == "external"
    assert "different APK build" in checks["android_apk_install_pairing_attempt"]["detail"]
    assert any("mobile:apk:wait-install-pair" in gate for gate in payload["remaining_external_gates"])


def test_docker_check_requires_engine_response(monkeypatch) -> None:
    fake_path = "C:/Docker/docker.exe"
    monkeypatch.setattr(readiness_module.shutil, "which", lambda name: fake_path if name == "docker" else None)

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:  # noqa: ANN002, ANN003
        return subprocess.CompletedProcess(args=args[0], returncode=1, stdout="", stderr="Cannot connect")

    monkeypatch.setattr(readiness_module.subprocess, "run", fake_run)

    check = readiness_module._docker_check()
    fields = readiness_module._docker_check_fields(check)

    assert check.success is False
    assert check.status == "external"
    assert check.evidence["docker_path"] == fake_path
    assert check.evidence["docker_version_returncode"] == 1
    assert "Docker Engine did not answer" in check.detail
    assert fields["docker_engine_status"] == "external"
    assert fields["docker_cli_path"] == fake_path
    assert fields["docker_server_version"] is None
    assert fields["docker_desktop_elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"


def test_docker_check_passes_when_engine_answers(monkeypatch) -> None:
    fake_path = "C:/Docker/docker.exe"
    monkeypatch.setattr(readiness_module.shutil, "which", lambda name: fake_path if name == "docker" else None)

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:  # noqa: ANN002, ANN003
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="28.1.1\n", stderr="")

    monkeypatch.setattr(readiness_module.subprocess, "run", fake_run)

    check = readiness_module._docker_check()
    fields = readiness_module._docker_check_fields(check)

    assert check.success is True
    assert check.status == "pass"
    assert check.evidence["docker_path"] == fake_path
    assert check.evidence["docker_server_version"] == "28.1.1"
    assert fields["docker_engine_status"] == "pass"
    assert fields["docker_cli_path"] == fake_path
    assert fields["docker_server_version"] == "28.1.1"
    assert fields["docker_desktop_elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert "server version 28.1.1" in check.detail


def test_docker_check_records_wsl_absence_when_windows_cli_missing(monkeypatch) -> None:
    monkeypatch.setattr(readiness_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(readiness_module.Path, "exists", lambda self: False)
    monkeypatch.setattr(readiness_module, "_docker_data_roots", lambda: ())
    monkeypatch.setattr(readiness_module, "_find_docker_data_executables", lambda roots: [])
    monkeypatch.setattr(readiness_module, "_windows_docker_services", lambda: [])
    monkeypatch.setattr(
        readiness_module,
        "_wsl_docker_evidence",
        lambda: {
            "checked": True,
            "distros": [{"name": "Ubuntu", "docker_path": None, "engine_available": False}],
            "engine_available": False,
        },
    )

    check = readiness_module._docker_check()

    assert check.success is False
    assert check.status == "external"
    assert check.evidence["wsl_docker"]["checked"] is True
    assert check.evidence["wsl_docker"]["distros"][0]["name"] == "Ubuntu"
    assert "WSL Docker was also checked" in check.detail


def test_wsl_distro_parser_ignores_no_installed_distribution_help_text() -> None:
    output = """
    Windows Subsystem for Linux has no installed distributions.

    You can resolve this by installing a distribution with the instructions below:

    Use 'wsl.exe --list --online' to list available distributions

    and 'wsl.exe --install <Distro>' to install.
    """

    assert readiness_module._wsl_output_says_no_distros(output) is True
    assert readiness_module._parse_wsl_distro_names(output) == []


def test_docker_check_reports_wsl_no_distros_without_fake_names(monkeypatch) -> None:
    monkeypatch.setattr(readiness_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(readiness_module.Path, "exists", lambda self: False)
    monkeypatch.setattr(readiness_module, "_docker_data_roots", lambda: ())
    monkeypatch.setattr(readiness_module, "_find_docker_data_executables", lambda roots: [])
    monkeypatch.setattr(readiness_module, "_windows_docker_services", lambda: [])
    monkeypatch.setattr(
        readiness_module,
        "_wsl_docker_evidence",
        lambda: {
            "checked": True,
            "no_distros": True,
            "wsl_list_stdout": "Windows Subsystem for Linux has no installed distributions.",
            "distros": [],
            "engine_available": False,
        },
    )

    check = readiness_module._docker_check()
    rendered = readiness_module.render_docker_engine_check(check)

    assert check.success is False
    assert check.evidence["wsl_docker"]["distros"] == []
    assert "WSL is installed but has no Linux distributions" in check.detail
    assert "WSL Docker was also checked across" not in check.detail
    assert "WSL distributions: none installed" in rendered


def test_docker_engine_diagnosis_render_includes_wsl_and_service_state(monkeypatch) -> None:
    monkeypatch.setattr(readiness_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(readiness_module.Path, "exists", lambda self: False)
    monkeypatch.setattr(readiness_module, "latest_docker_desktop_install_attempt", lambda: None)
    monkeypatch.setattr(readiness_module, "_docker_data_roots", lambda: (Path("C:/ProgramData/DockerDesktop"),))
    monkeypatch.setattr(readiness_module, "_find_docker_data_executables", lambda roots: [])
    monkeypatch.setattr(
        readiness_module,
        "_windows_docker_services",
        lambda: [{"name": "com.docker.service", "display_name": "Docker Desktop Service", "status": "Stopped"}],
    )
    monkeypatch.setattr(
        readiness_module,
        "_wsl_docker_evidence",
        lambda: {
            "checked": True,
            "distros": [{"name": "Ubuntu", "docker_path": None, "engine_available": False}],
            "engine_available": False,
        },
    )

    check = readiness_module.run_docker_engine_check()
    payload = readiness_module.docker_check_to_dict(check)
    rendered = readiness_module.render_docker_engine_check(check)

    assert payload["check_id"] == "docker_cli"
    assert payload["success"] is False
    assert "CAS Forex Docker Engine diagnosis" in rendered
    assert "WSL checked: true" in rendered
    assert "com.docker.service: Stopped" in rendered
    assert 'docker version --format "{{.Server.Version}}"' in rendered


def test_docker_check_reports_winget_install_command_and_wsl_warnings(monkeypatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "winget":
            return "C:/Users/wakil/AppData/Local/Microsoft/WindowsApps/winget.exe"
        return None

    monkeypatch.setattr(readiness_module.shutil, "which", fake_which)
    monkeypatch.setattr(readiness_module.Path, "exists", lambda self: False)
    monkeypatch.setattr(
        readiness_module,
        "latest_docker_desktop_install_attempt",
        lambda: {
            "status": "admin_elevation_required",
            "detail": "Docker Desktop installer was reached through winget, but installation requires administrator elevation.",
            "returncode": 4294967291,
            "admin_elevation_required": True,
        },
    )
    monkeypatch.setattr(readiness_module, "_docker_data_roots", lambda: ())
    monkeypatch.setattr(readiness_module, "_find_docker_data_executables", lambda roots: [])
    monkeypatch.setattr(readiness_module, "_windows_docker_services", lambda: [])
    monkeypatch.setattr(
        readiness_module,
        "_wsl_docker_evidence",
        lambda: {
            "checked": True,
            "wsl_list_stderr": "wsl: Invalid boolean value 'false[boot]' for key 'interop.appendWindowsPath'",
            "distros": [
                {
                    "name": "Ubuntu",
                    "docker_path": None,
                    "engine_available": False,
                    "stderr": "sh: 1: docker: not found",
                }
            ],
            "engine_available": False,
        },
    )

    check = readiness_module._docker_check()
    rendered = readiness_module.render_docker_engine_check(check)

    assert check.success is False
    assert check.evidence["docker_desktop_winget_available"] is True
    assert check.evidence["docker_desktop_install_command"] == (
        "winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements"
    )
    assert check.evidence["docker_desktop_elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert check.evidence["docker_desktop_install_attempt"]["status"] == "admin_elevation_required"
    assert "Docker Desktop can be installed with: winget install --id Docker.DockerDesktop" in check.detail
    assert "If Windows asks for administrator elevation, use: npm --prefix ui run mobile:docker-install-elevated" in check.detail
    assert "Last Docker Desktop install attempt: admin_elevation_required" in check.detail
    assert "Invalid boolean value" in check.detail
    assert "Docker Desktop install command: winget install --id Docker.DockerDesktop" in rendered
    assert "Docker Desktop elevated install command: npm --prefix ui run mobile:docker-install-elevated" in rendered
    assert "Last Docker Desktop install attempt: admin_elevation_required" in rendered
    assert "WSL warnings:" in rendered
    assert "docker: not found" in rendered


def test_docker_check_passes_when_wsl_engine_answers(monkeypatch) -> None:
    monkeypatch.setattr(readiness_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(readiness_module.Path, "exists", lambda self: False)
    monkeypatch.setattr(readiness_module, "_docker_data_roots", lambda: ())
    monkeypatch.setattr(readiness_module, "_find_docker_data_executables", lambda roots: [])
    monkeypatch.setattr(readiness_module, "_windows_docker_services", lambda: [])
    monkeypatch.setattr(
        readiness_module,
        "_wsl_docker_evidence",
        lambda: {
            "checked": True,
            "distros": [
                {
                    "name": "Ubuntu",
                    "docker_path": "/usr/bin/docker",
                    "server_version": "28.2.0",
                    "engine_available": True,
                }
            ],
            "engine_available": True,
            "engine_distro": "Ubuntu",
            "server_version": "28.2.0",
            "docker_path": "/usr/bin/docker",
        },
    )

    check = readiness_module._docker_check()

    assert check.success is True
    assert check.status == "pass"
    assert check.evidence["wsl_docker"]["engine_available"] is True
    assert "inside WSL distro Ubuntu" in check.detail
