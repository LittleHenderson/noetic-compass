"""Tests for the CAS Forex web/PWA/APK phone smoke checker."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from cas_forex.web_phone_smoke import HttpSmokeResponse, run_web_phone_smoke


def _response(body: str | dict, status_code: int = 200) -> HttpSmokeResponse:
    if isinstance(body, dict):
        body = json.dumps(body)
    return HttpSmokeResponse(status_code=status_code, body=body.encode("utf-8"), headers={})


def _ok_transport(
    method: str,
    url: str,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
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
        return _response(
            {
                "report_kind": "cas_forex_owner_auth",
                "pairing_urls": [
                    "http://phone-preview.test/?page=quick-start#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2Fphone-preview.test%2Fapi%2Fforex",
                ],
            }
        )
    if url.endswith("/api/forex/mobile/phone-proof") and method == "POST":
        assert body is not None
        payload = json.loads(body.decode("utf-8"))
        assert payload["dry_run"] is True
        assert headers
        assert headers["X-CAS-Owner-Token"] == "secret-token"
        assert headers["X-Forwarded-For"] == "10.0.0.55"
        assert headers["X-CAS-Client-API-Base"].endswith("/api/forex")
        return _response(
            {
                "report_kind": "cas_forex_phone_runtime_proof",
                "status": "DRY_RUN_NOT_RECORDED",
                "dry_run": True,
                "phone_browser_verified": True,
                "device_class": "phone",
                "client_host_source": "x-forwarded-for",
                "effective_client_host": "10.0.0.55",
                "api_base_network_path": "same_origin_proxy",
            }
        )
    return _response('<html><head><link rel="manifest" href="/manifest.webmanifest"></head><body><div id="root"></div></body></html>')


def _write_dist(path: Path, *, index: str = '<div id="root"></div>') -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(index, encoding="utf-8")
    (path / "manifest.webmanifest").write_text('{"display":"standalone"}', encoding="utf-8")
    (path / "sw.js").write_text("precacheAndRoute([]);", encoding="utf-8")


def _write_apk(path: Path, dist: Path, *, stale_index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in ("index.html", "manifest.webmanifest", "sw.js"):
            source = dist / name
            data = source.read_bytes()
            if stale_index and name == "index.html":
                data = b"<html>stale</html>"
            archive.writestr(f"assets/public/{name}", data)
        archive.writestr("assets/padding.bin", b"0" * 1_200_000)


def test_web_phone_smoke_passes_when_shell_pwa_proxy_and_apk_exist(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)

    report = run_web_phone_smoke(
        web_base="http://phone-preview.test",
        apk_path=apk,
        web_dist_dir=dist,
        transport=_ok_transport,
    )

    assert report.failed == 0
    assert report.passed == report.total_checks == 7
    assert {result.check_id for result in report.results} == {
        "app_shell",
        "pwa_manifest",
        "service_worker",
        "same_origin_api_proxy",
        "phone_proof_proxy_dry_run",
        "android_debug_apk",
        "android_apk_web_assets",
    }


def test_web_phone_smoke_flags_self_destroying_worker(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)

    def transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/sw.js"):
            return _response("selfDestroying unregister precacheAndRoute NavigationRoute /api")
        return _ok_transport(method, url, timeout_seconds, headers, body)

    report = run_web_phone_smoke(apk_path=apk, web_dist_dir=dist, transport=transport)
    [hit] = [result for result in report.results if result.check_id == "service_worker"]
    assert hit.success is False
    assert "self-destroying" in hit.detail


def test_web_phone_smoke_flags_unhealthy_same_origin_proxy(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)

    def transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpSmokeResponse:
        if url.endswith("/api/forex/health"):
            return _response({"status": "warming"}, status_code=200)
        return _ok_transport(method, url, timeout_seconds, headers, body)

    report = run_web_phone_smoke(apk_path=apk, web_dist_dir=dist, transport=transport)
    [hit] = [result for result in report.results if result.check_id == "same_origin_api_proxy"]
    assert hit.success is False
    assert "warming" in hit.detail


def test_web_phone_smoke_uses_loopback_pairing_for_lan_owner_token(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)
    pairing_urls: list[str] = []

    def transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpSmokeResponse:  # noqa: ARG001
        if url == "http://10.0.0.6:4173/api/forex/owner-auth/pairing":
            pairing_urls.append(url)
            return _response({"error": "owner_auth_required"}, status_code=401)
        if url == "http://127.0.0.1:4173/api/forex/owner-auth/pairing":
            pairing_urls.append(url)
            return _response(
                {
                    "report_kind": "cas_forex_owner_auth",
                    "pairing_urls": [
                        "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex",
                    ],
                }
            )
        return _ok_transport(method, url, timeout_seconds, headers, body)

    report = run_web_phone_smoke(
        web_base="http://10.0.0.6:4173",
        apk_path=apk,
        web_dist_dir=dist,
        transport=transport,
    )
    hit = {result.check_id: result for result in report.results}["phone_proof_proxy_dry_run"]

    assert hit.success is True
    assert pairing_urls == [
        "http://10.0.0.6:4173/api/forex/owner-auth/pairing",
        "http://127.0.0.1:4173/api/forex/owner-auth/pairing",
    ]


def test_web_phone_smoke_retries_transient_phone_proof_proxy_timeout(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)
    proof_attempts = 0

    def transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpSmokeResponse:
        nonlocal proof_attempts
        if url.endswith("/api/forex/mobile/phone-proof") and method == "POST":
            proof_attempts += 1
            if proof_attempts == 1:
                raise TimeoutError("first phone-proof proxy hop stalled")
        return _ok_transport(method, url, timeout_seconds, headers, body)

    report = run_web_phone_smoke(
        web_base="http://phone-preview.test",
        apk_path=apk,
        web_dist_dir=dist,
        transport=transport,
    )
    hit = {result.check_id: result for result in report.results}["phone_proof_proxy_dry_run"]

    assert report.failed == 0
    assert proof_attempts == 2
    assert hit.success is True
    assert hit.attempts == 2


def test_web_phone_smoke_flags_missing_apk(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_dist(dist)
    report = run_web_phone_smoke(
        apk_path=tmp_path / "missing.apk",
        web_dist_dir=dist,
        transport=_ok_transport,
    )
    [hit] = [result for result in report.results if result.check_id == "android_debug_apk"]
    assert hit.success is False
    assert "APK not found" in hit.detail


def test_web_phone_smoke_default_timeout_allows_phone_lan_first_touch(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)
    seen_timeouts: list[float] = []

    def transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpSmokeResponse:
        seen_timeouts.append(timeout_seconds)
        return _ok_transport(method, url, timeout_seconds, headers, body)

    report = run_web_phone_smoke(apk_path=apk, web_dist_dir=dist, transport=transport)

    assert report.failed == 0
    assert seen_timeouts
    assert all(timeout == 10.0 for timeout in seen_timeouts)


def test_web_phone_smoke_can_verify_cloud_api_token_boundary(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist)

    def transport(
        method: str,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpSmokeResponse:  # noqa: ARG001
        if url.endswith("/api/forex/owner-auth/state"):
            if headers and headers.get("X-CAS-Owner-Token") == "secret-token":
                return _response({"report_kind": "cas_forex_owner_auth", "token_present": True})
            return _response({"error": "owner_auth_required"}, status_code=401)
        return _ok_transport(method, url, timeout_seconds, headers, body)

    report = run_web_phone_smoke(
        apk_path=apk,
        web_dist_dir=dist,
        transport=transport,
        check_cloud_api_auth=True,
        owner_token="secret-token",
    )

    hits = {result.check_id: result for result in report.results}
    assert hits["cloud_api_without_token"].success is True
    assert hits["cloud_api_with_token"].success is True


def test_web_phone_smoke_flags_stale_apk_web_assets(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    dist = tmp_path / "dist"
    _write_dist(dist)
    _write_apk(apk, dist, stale_index=True)

    report = run_web_phone_smoke(apk_path=apk, web_dist_dir=dist, transport=_ok_transport)
    hit = {result.check_id: result for result in report.results}["android_apk_web_assets"]

    assert hit.success is False
    assert "differ from ui/dist" in hit.detail
    assert "index.html" in hit.detail
