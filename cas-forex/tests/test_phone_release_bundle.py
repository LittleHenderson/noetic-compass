"""Tests for CAS Forex phone release evidence bundles."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof
from cas_forex.mobile_phone_proof import record_phone_runtime_proof
from cas_forex.phone_release_bundle import build_phone_release_bundle
from cas_forex.web_phone_smoke import HttpSmokeResponse


def _response(body: str | dict, status_code: int = 200) -> HttpSmokeResponse:
    if isinstance(body, dict):
        body = json.dumps(body)
    return HttpSmokeResponse(status_code=status_code, body=body.encode("utf-8"), headers={})


def _ok_transport(
    method: str,
    url: str,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
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
    return _response('<html><head><link rel="manifest" href="/manifest.webmanifest"></head><body><div id="root"></div></body></html>')


def _write_apk(path: Path, dist: Path, *, stale_index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in ("index.html", "manifest.webmanifest", "sw.js"):
            data = (dist / name).read_bytes()
            if stale_index and name == "index.html":
                data = b"<html>stale</html>"
            archive.writestr(f"assets/public/{name}", data)
        archive.writestr("assets/padding.bin", b"0" * 1_200_000)


def test_phone_release_bundle_writes_manifest_readme_smoke_and_apk_copy(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    output = root / "evidence_runs" / "web_phone_release" / "latest"
    dist.mkdir(parents=True)
    apk.parent.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist)

    bundle = build_phone_release_bundle(
        workspace_root=root,
        output_dir=output,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
    )

    assert bundle.ready_for_phone_install is True
    assert (output / "phone_release_bundle.json").exists()
    assert (output / "web_phone_smoke.json").exists()
    assert (output / "mobile_release_readiness.json").exists()
    assert (output / "README.md").exists()
    copied_apk = output / "cas-forex-debug.apk"
    assert copied_apk.exists()
    manifest = json.loads((output / "phone_release_bundle.json").read_text(encoding="utf-8"))
    rendered_manifest = json.dumps(manifest)
    assert manifest["ready_for_phone_install"] is True
    assert manifest["tested_web_base"] == "http://phone-preview.test"
    assert manifest["tested_quick_start_url"] == "http://phone-preview.test/?page=quick-start"
    assert manifest["phone_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert manifest["package_ready_for_phone_install"] is True
    assert manifest["phone_browser_observed"] is False
    assert manifest["phone_browser_verified"] is False
    assert manifest["phone_proof_fresh"] is False
    assert manifest["phone_observation_fresh"] is False
    assert manifest["apk_install_pairing_attempt_status"] == "none"
    assert "android_device_ready" in manifest
    assert "android_device_count" in manifest
    assert "android_device_detail" in manifest
    assert "android_adb_path" in manifest
    assert "docker_engine_status" in manifest
    assert "docker_engine_detail" in manifest
    assert manifest["install_test_required_artifact_ids"] == [
        "android_debug_apk",
        "web_index",
        "pwa_manifest",
        "service_worker",
    ]
    assert manifest["missing_install_test_required_artifacts"] == []
    assert manifest["signed_release_apk_present"] is False
    assert manifest["signed_release_apk_sha256"] is None
    assert manifest["smoke_report"]["failed"] == 0
    assert manifest["mobile_readiness_report"]["package_ready_for_phone_install"] is True
    assert manifest["phone_verification_runbook"]["tested_web_base"] == "http://phone-preview.test"
    assert manifest["phone_verification_runbook"]["tested_quick_start_url"] == "http://phone-preview.test/?page=quick-start"
    assert manifest["phone_verification_runbook"]["phone_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert manifest["phone_verification_runbook"]["current_phone_proof_fresh"] is False
    assert manifest["phone_verification_runbook"]["current_phone_proof_age_seconds"] is None
    assert manifest["phone_verification_runbook"]["current_phone_observation_fresh"] is False
    assert manifest["phone_verification_runbook"]["current_apk_runtime_status"] == "none"
    assert manifest["phone_verification_runbook"]["current_apk_runtime_observed"] is False
    assert manifest["phone_verification_runbook"]["current_apk_install_pairing_attempt_status"] == "none"
    assert manifest["phone_verification_runbook"]["current_android_release_signing_status"] == "missing_config"
    assert manifest["phone_verification_runbook"]["current_android_release_signing_ready"] is False
    assert manifest["phone_verification_runbook"]["pairing_context"]["pwa_api_base"] == "http://10.0.0.6:4173/api/forex"
    assert manifest["phone_verification_runbook"]["pairing_context"]["direct_api_base"] == "http://10.0.0.6:8765/api/forex"
    assert manifest["phone_verification_runbook"]["apk_install_pairing_proof_path"].endswith("android_apk_install_pairing_proof.json")
    runbook_steps = "\n".join(manifest["phone_verification_runbook"]["steps"])
    assert "open http://10.0.0.6:4173/?page=quick-start" in runbook_steps
    assert "watch_mobile_phone_proof.py --exit-code-on-missing" in runbook_steps
    assert "android_apk_install_pairing_proof.json" in runbook_steps
    assert "confirm phone_browser_verified=true" in runbook_steps
    assert "npm --prefix ui run mobile:apk:release" in runbook_steps
    assert "app delivery, pairing, and network reachability" in manifest["phone_verification_runbook"]["verification_scope"]
    assert "owner-authorized runtime gates" in manifest["phone_verification_runbook"]["claim_boundary"]
    assert "does not grant" not in manifest["phone_verification_runbook"]["claim_boundary"]
    assert "secret-owner-token" not in rendered_manifest
    assert "cas_owner_token=REDACTED" in rendered_manifest
    assert "secret-owner-token" not in (output / "mobile_release_readiness.json").read_text(encoding="utf-8")
    artifacts = {artifact["artifact_id"]: artifact for artifact in manifest["artifacts"]}
    assert artifacts["android_debug_apk"]["sha256"] == artifacts["release_bundle_debug_apk_copy"]["sha256"]
    assert artifacts["android_release_apk"]["exists"] is False
    assert artifacts["web_index"]["exists"] is True
    assert "Open Quick Start from a real phone" in manifest["remaining_external_gates"][0]
    assert "mobile:apk:wait-install-pair" in manifest["remaining_external_gates"][1]
    readme = (output / "README.md").read_text(encoding="utf-8")
    assert "Install-test required artifacts" in readme
    assert "Missing install-test required artifacts: `none`" in readme
    assert "Signed release APK: `missing`" in readme
    assert "## Phone Verification Runbook" in readme
    assert "Tested phone web URL" in readme
    assert "Tested Quick Start URL" in readme
    assert "Phone-reachable Quick Start URL" in readme
    assert "http://phone-preview.test/?page=quick-start" in readme
    assert "http://10.0.0.6:4173/?page=quick-start" in readme
    assert "Current phone browser observed" in readme
    assert "Current phone browser verified" in readme
    assert "Current phone proof freshness" in readme
    assert "Current phone observation freshness" in readme
    assert "Current APK runtime" in readme
    assert "Current APK install-pair attempt" in readme
    assert "Current Android release signing" in readme
    assert "Verification scope" in readme
    assert "owner-authorized runtime gates" in readme
    assert "does not grant" not in readme
    assert "confirm phone_browser_verified=true" in readme
    assert "watch_mobile_phone_proof.py --exit-code-on-missing" in readme
    assert "secret-owner-token" not in readme
    assert "cas_owner_token=REDACTED" in readme
    assert "mobile_release_readiness.json" in readme
    assert "run_mobile_release_readiness.py" in readme
    assert "run_mobile_stack_readiness.py" in readme
    assert "npm --prefix ui run mobile:readiness" in readme
    assert "npm --prefix ui run mobile:proof-session" in readme
    assert "npm --prefix ui run mobile:apk:install-pair" in readme
    assert "npm --prefix ui run mobile:apk:wait-install-pair" in readme
    assert "npm --prefix ui run mobile:apk:release" in readme
    assert "npm --prefix ui run mobile:apk:pair" in readme
    assert "npm --prefix ui run mobile:docker-check" in readme
    assert "android_apk_install_pairing_proof.json" in readme
    assert "--launch-native-pairing" in readme
    assert "redacts the owner token" in readme


def test_phone_release_bundle_selects_pairing_context_for_tested_lan_host(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    output = root / "evidence_runs" / "web_phone_release" / "latest"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist)

    def multi_adapter_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
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

    build_phone_release_bundle(
        workspace_root=root,
        output_dir=output,
        web_base="http://172.16.8.129:4173",
        apk_path=apk,
        transport=multi_adapter_transport,
    )
    manifest = json.loads((output / "phone_release_bundle.json").read_text(encoding="utf-8"))
    pairing = manifest["phone_verification_runbook"]["pairing_context"]

    assert manifest["phone_quick_start_url"] == "http://172.16.8.129:4173/?page=quick-start"
    assert pairing["pwa_api_base"] == "http://172.16.8.129:4173/api/forex"
    assert pairing["direct_api_base"] == "http://172.16.8.129:8765/api/forex"
    assert pairing["redacted_pairing_url"].startswith("http://172.16.8.129:4173/")
    assert "172.16.8.129%3A8765" in pairing["redacted_native_pairing_url"]


def test_phone_release_bundle_copies_release_apk_when_present(monkeypatch, tmp_path: Path) -> None:
    for name in (
        "CAS_FOREX_ANDROID_STOREFILE",
        "CAS_FOREX_ANDROID_STOREPASSWORD",
        "CAS_FOREX_ANDROID_KEYALIAS",
        "CAS_FOREX_ANDROID_KEYPASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    debug_apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    release_apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
    output = root / "evidence_runs" / "web_phone_release" / "latest"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(debug_apk, dist)
    release_apk.parent.mkdir(parents=True)
    release_apk.write_bytes(b"signed-release-apk")

    build_phone_release_bundle(
        workspace_root=root,
        output_dir=output,
        web_base="http://phone-preview.test",
        apk_path=debug_apk,
        release_apk_path=release_apk,
        transport=_ok_transport,
    )

    manifest = json.loads((output / "phone_release_bundle.json").read_text(encoding="utf-8"))
    artifacts = {artifact["artifact_id"]: artifact for artifact in manifest["artifacts"]}
    copied_release_apk = output / "cas-forex-release.apk"

    assert copied_release_apk.exists()
    assert manifest["signed_release_apk_present"] is True
    assert manifest["signed_release_apk_sha256"] == artifacts["android_release_apk"]["sha256"]
    assert manifest["signed_release_apk_size_bytes"] == artifacts["android_release_apk"]["size_bytes"]
    assert artifacts["android_release_apk"]["exists"] is True
    assert artifacts["android_release_apk"]["sha256"] == artifacts["release_bundle_release_apk_copy"]["sha256"]
    assert manifest["phone_verification_runbook"]["copied_release_apk"] == str(copied_release_apk)
    assert "Copied release APK" in (output / "README.md").read_text(encoding="utf-8")


def test_phone_release_bundle_not_ready_when_smoke_fails(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    dist.mkdir(parents=True)
    apk.parent.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist)

    def failing_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/health"):
            return _response({"status": "warming"}, status_code=200)
        return _ok_transport(method, url, timeout_seconds, headers)

    bundle = build_phone_release_bundle(
        workspace_root=root,
        output_dir=root / "evidence_runs" / "web_phone_release" / "latest",
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=failing_transport,
    )

    assert bundle.ready_for_phone_install is False
    assert bundle.smoke_report["failed"] == 1


def test_phone_release_bundle_readme_summarizes_latest_failed_apk_attempt(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    output = root / "evidence_runs" / "web_phone_release" / "latest"
    dist.mkdir(parents=True)
    apk.parent.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist)
    record_android_apk_install_pairing_proof(
        workspace_root=root,
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

    build_phone_release_bundle(
        workspace_root=root,
        output_dir=output,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
    )

    manifest = json.loads((output / "phone_release_bundle.json").read_text(encoding="utf-8"))
    readme = (output / "README.md").read_text(encoding="utf-8")

    assert manifest["phone_verification_runbook"]["current_apk_install_pairing_attempt_status"] == "install_failed"
    assert manifest["apk_install_pairing_attempt_status"] == "install_failed"
    assert manifest["apk_install_pairing_attempt_message"] == "No ready Android device is attached."
    assert manifest["tested_quick_start_url"] == "http://phone-preview.test/?page=quick-start"
    assert manifest["phone_quick_start_url"] == "http://10.0.0.6:4173/?page=quick-start"
    assert "Current APK install-pair attempt" in readme
    assert "install_failed" in readme
    assert "No ready Android device is attached." in readme


def test_phone_release_bundle_readme_summarizes_latest_apk_runtime(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    output = root / "evidence_runs" / "web_phone_release" / "latest"
    dist.mkdir(parents=True)
    apk.parent.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist)
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
        workspace_root=root,
        client_host="10.0.0.55",
        client_api_base="http://10.0.0.6:8765/api/forex",
    )

    build_phone_release_bundle(
        workspace_root=root,
        output_dir=output,
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
    )

    manifest = json.loads((output / "phone_release_bundle.json").read_text(encoding="utf-8"))
    readme = (output / "README.md").read_text(encoding="utf-8")

    assert manifest["mobile_readiness_report"]["physical_phone_verified"] is False
    assert manifest["mobile_readiness_report"]["apk_runtime_verified"] is True
    assert manifest["phone_verification_runbook"]["current_apk_runtime_status"] == "verified"
    assert manifest["phone_verification_runbook"]["current_apk_runtime_verified"] is True
    assert "Current APK runtime" in readme
    assert "verified" in readme
    assert "non-local phone/API path" in readme
    assert "mobile:apk:wait-install-pair" in manifest["remaining_external_gates"][0]


def test_phone_release_bundle_not_ready_when_mobile_readiness_fails(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    dist.mkdir(parents=True)
    apk.parent.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist)

    def malformed_pairing_transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/owner-auth/pairing"):
            return _response({"report_kind": "cas_forex_owner_auth", "pairing_urls": []})
        return _ok_transport(method, url, timeout_seconds, headers)

    bundle = build_phone_release_bundle(
        workspace_root=root,
        output_dir=root / "evidence_runs" / "web_phone_release" / "latest",
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=malformed_pairing_transport,
    )

    assert bundle.smoke_report["failed"] == 0
    assert bundle.mobile_readiness_report["package_ready_for_phone_install"] is False
    assert bundle.ready_for_phone_install is False
    assert "failed mobile readiness checks" in bundle.summary


def test_phone_release_bundle_not_ready_when_apk_web_assets_are_stale(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    dist = root / "ui" / "dist"
    apk = root / "ui" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (dist / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")
    _write_apk(apk, dist, stale_index=True)

    bundle = build_phone_release_bundle(
        workspace_root=root,
        output_dir=root / "evidence_runs" / "web_phone_release" / "latest",
        web_base="http://phone-preview.test",
        apk_path=apk,
        transport=_ok_transport,
    )

    assert bundle.ready_for_phone_install is False
    assert bundle.smoke_report["failed"] == 1
    smoke_results = {result["check_id"]: result for result in bundle.smoke_report["results"]}
    assert smoke_results["android_apk_web_assets"]["success"] is False
    assert "index.html" in smoke_results["android_apk_web_assets"]["detail"]
