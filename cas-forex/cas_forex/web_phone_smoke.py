"""Web/PWA/APK smoke checks for CAS Forex phone readiness.

The checker is observational only. It proves the owner-facing phone/web shell
is being served, the PWA assets are installable, the same-origin API proxy works,
and the Android debug APK artifact exists when requested. It does not touch
broker, payment, or trading actions.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import parse_qs, urljoin, urlsplit


@dataclass(frozen=True)
class HttpSmokeResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str]

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class WebPhoneCheckResult:
    check_id: str
    success: bool
    detail: str
    status_code: Optional[int] = None
    elapsed_ms: float = 0.0
    attempts: int = 1


@dataclass(frozen=True)
class WebPhoneSmokeReport:
    web_base: str
    apk_path: str
    total_checks: int
    passed: int
    failed: int
    elapsed_ms: float
    results: tuple[WebPhoneCheckResult, ...]
    plain_english_summary: str


Transport = Callable[[str, str, float, Mapping[str, str], bytes | None], HttpSmokeResponse]

_PROBE_MAX_ATTEMPTS = 2
_RETRYABLE_STATUS_CODES = {502, 503, 504}


def _default_transport(
    method: str,
    url: str,
    timeout_seconds: float,
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
) -> HttpSmokeResponse:
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return HttpSmokeResponse(
                status_code=int(response.status),
                body=response.read(),
                headers=dict(response.headers.items()),
            )
    except urllib.error.HTTPError as exc:
        return HttpSmokeResponse(
            status_code=int(exc.code),
            body=exc.read(),
            headers=dict(exc.headers.items()),
        )


def _join(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _http_check(
    check_id: str,
    url: str,
    *,
    method: str = "GET",
    transport: Transport,
    timeout_seconds: float,
    validator: Callable[[HttpSmokeResponse], tuple[bool, str]],
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    max_attempts: int = 1,
) -> WebPhoneCheckResult:
    started = time.perf_counter()
    attempts = 0
    last_exc: Exception | None = None
    for attempts in range(1, max(1, max_attempts) + 1):
        try:
            response = _call_transport(transport, method, url, timeout_seconds, dict(headers or {}), body)
            if response.status_code in _RETRYABLE_STATUS_CODES and attempts < max_attempts:
                _sleep_before_retry(attempts)
                continue
            success, detail = validator(response)
            return WebPhoneCheckResult(
                check_id=check_id,
                success=success,
                detail=detail,
                status_code=response.status_code,
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                attempts=attempts,
            )
        except Exception as exc:
            last_exc = exc
            if attempts < max_attempts:
                _sleep_before_retry(attempts)
                continue
            break
    detail = (
        f"{type(last_exc).__name__}: {last_exc}"
        if last_exc is not None
        else "probe did not complete"
    )
    return WebPhoneCheckResult(
        check_id=check_id,
        success=False,
        detail=detail,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        attempts=max(1, attempts),
    )


def _sleep_before_retry(attempt: int) -> None:
    time.sleep(min(0.25 * max(1, attempt), 0.75))


def _call_transport(
    transport: Transport,
    method: str,
    url: str,
    timeout_seconds: float,
    headers: Mapping[str, str],
    body: bytes | None = None,
) -> HttpSmokeResponse:
    try:
        return transport(method, url, timeout_seconds, headers, body)
    except TypeError:
        legacy_transport = transport  # type: ignore[assignment]
        return legacy_transport(method, url, timeout_seconds, headers)  # type: ignore[misc]


def _index_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    text = response.text
    if response.status_code != 200:
        return False, f"index returned HTTP {response.status_code}"
    if '<div id="root">' not in text and 'id="root"' not in text:
        return False, "index did not contain the React root"
    if "manifest.webmanifest" not in text:
        return False, "index did not link the web manifest"
    return True, "app shell served"


def _manifest_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    if response.status_code != 200:
        return False, f"manifest returned HTTP {response.status_code}"
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        return False, f"manifest was not valid JSON: {exc}"
    if payload.get("display") != "standalone":
        return False, "manifest display is not standalone"
    if payload.get("start_url") is None:
        return False, "manifest missing start_url"
    icons = payload.get("icons")
    if not isinstance(icons, list) or len(icons) < 2:
        return False, "manifest missing phone icon set"
    return True, "PWA manifest served"


def _service_worker_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    text = response.text
    if response.status_code != 200:
        return False, f"service worker returned HTTP {response.status_code}"
    if "precacheAndRoute" not in text:
        return False, "service worker missing precache"
    if "NavigationRoute" not in text or "/api" not in text:
        return False, "service worker does not visibly deny API navigation caching"
    lowered = text.lower()
    if "unregister" in lowered or "selfdestroying" in lowered:
        return False, "service worker still looks self-destroying"
    return True, "generated service worker served"


def _api_proxy_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    if response.status_code != 200:
        return False, f"proxied health returned HTTP {response.status_code}"
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        return False, f"proxied health was not JSON: {exc}"
    if payload.get("status") != "healthy":
        return False, f"proxied health status was {payload.get('status')!r}"
    return True, "same-origin API proxy healthy"


def _protected_api_without_token_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    if response.status_code != 401:
        return False, f"protected API without token returned HTTP {response.status_code}, expected 401"
    text = response.text
    if "owner_auth_required" not in text and "Owner token required" not in text:
        return False, "401 response did not look like owner-auth denial"
    return True, "protected API refused no-token request"


def _protected_api_with_token_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    if response.status_code != 200:
        return False, f"protected API with token returned HTTP {response.status_code}"
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        return False, f"protected API with token was not JSON: {exc}"
    if payload.get("report_kind") != "cas_forex_owner_auth":
        return False, f"protected API returned unexpected report_kind {payload.get('report_kind')!r}"
    return True, "protected API accepted owner token"


def _phone_proof_proxy_dry_run_payload(web_base: str, api_base: str | None = None) -> dict[str, Any]:
    base = web_base.rstrip("/")
    api = (api_base or f"{base}/api/forex").rstrip("/")
    return {
        "source": "web-phone-smoke",
        "app_surface": "pwa",
        "url_origin": base,
        "url_path": "/?page=quick-start",
        "api_base": api,
        "display_mode": "standalone",
        "standalone_pwa": True,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
            "Mobile/15E148 Safari/604.1"
        ),
        "platform": "iPhone",
        "language": "en-US",
        "timezone": "America/Los_Angeles",
        "viewport_width": 390,
        "viewport_height": 844,
        "screen_width": 390,
        "screen_height": 844,
        "device_pixel_ratio": 3,
        "max_touch_points": 5,
        "online": True,
        "dry_run": True,
    }


def _phone_proof_proxy_dry_run_validator(response: HttpSmokeResponse) -> tuple[bool, str]:
    if response.status_code != 200:
        return False, f"phone-proof dry-run returned HTTP {response.status_code}"
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        return False, f"phone-proof dry-run was not JSON: {exc}"
    if payload.get("dry_run") is not True or payload.get("status") != "DRY_RUN_NOT_RECORDED":
        return False, "phone-proof dry-run was not marked non-persistent"
    if payload.get("phone_browser_verified") is not True:
        return False, f"phone-proof dry-run did not verify phone proof: {payload.get('device_class')!r}"
    effective_client_host = payload.get("effective_client_host")
    if not isinstance(effective_client_host, str) or _is_loopback_host(effective_client_host):
        return False, f"phone-proof dry-run saw loopback or missing client host {effective_client_host!r}"
    if payload.get("local_runtime_only") is True:
        return False, "phone-proof dry-run was still classified as localhost-only"
    if payload.get("client_host_source") not in {"x-forwarded-for", "request-client", "x-real-ip"}:
        return False, f"phone-proof dry-run used unexpected client host source: {payload.get('client_host_source')!r}"
    if payload.get("api_base_network_path") != "same_origin_proxy":
        return False, f"phone-proof dry-run saw unexpected API path {payload.get('api_base_network_path')!r}"
    if payload.get("source_path"):
        return False, "phone-proof dry-run returned a persisted source_path"
    return True, "same-origin phone-proof proxy dry-run verified without writing evidence"


def _is_loopback_host(host: str) -> bool:
    cleaned = host.strip().strip("[]").lower()
    if cleaned in {"localhost", "::1"}:
        return True
    try:
        parsed = ip_address(cleaned)
    except ValueError:
        return False
    mapped = getattr(parsed, "ipv4_mapped", None)
    if mapped is not None:
        return mapped.is_loopback
    return parsed.is_loopback


def _pairing_context_from_pairing_payload(
    *,
    web_base: str,
    transport: Transport,
    timeout_seconds: float,
) -> dict[str, str]:
    pairing_urls = [_join(web_base, "/api/forex/owner-auth/pairing")]
    loopback_pairing_url = _loopback_pairing_url(web_base)
    if loopback_pairing_url not in pairing_urls:
        pairing_urls.append(loopback_pairing_url)
    response: HttpSmokeResponse | None = None
    for url in pairing_urls:
        response = None
        for attempt in range(1, _PROBE_MAX_ATTEMPTS + 1):
            try:
                response = _call_transport(
                    transport,
                    "GET",
                    url,
                    timeout_seconds,
                    {},
                )
            except Exception:
                if attempt < _PROBE_MAX_ATTEMPTS:
                    _sleep_before_retry(attempt)
                continue
            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _PROBE_MAX_ATTEMPTS:
                _sleep_before_retry(attempt)
                continue
            break
        if response is None:
            continue
        if response.status_code == 200:
            break
        if response.status_code not in {401, 403}:
            break
    if not response or response.status_code != 200:
        return {}
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError:
        return {}
    urls = payload.get("pairing_urls")
    if not isinstance(urls, list) or not urls:
        return {}
    first = urls[0]
    if not isinstance(first, str):
        return {}
    try:
        parsed = urlsplit(first)
    except ValueError:
        return {}
    hash_params = parse_qs(parsed.fragment)
    query_params = parse_qs(parsed.query)
    out: dict[str, str] = {}
    token_values = hash_params.get("cas_owner_token") or query_params.get("cas_owner_token") or []
    token = token_values[0] if token_values else None
    if isinstance(token, str) and token:
        out["owner_token"] = token
    api_values = hash_params.get("cas_api_base") or query_params.get("cas_api_base") or []
    api_base = api_values[0] if api_values else None
    if isinstance(api_base, str) and api_base:
        out["api_base"] = api_base.rstrip("/")
    if parsed.scheme and parsed.netloc:
        out["phone_origin"] = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return out


def _loopback_pairing_url(web_base: str) -> str:
    try:
        parsed = urlsplit(web_base)
    except ValueError:
        return "http://127.0.0.1:4173/api/forex/owner-auth/pairing"
    scheme = parsed.scheme or "http"
    port = parsed.port or (443 if scheme == "https" else 80)
    return f"{scheme}://127.0.0.1:{port}/api/forex/owner-auth/pairing"


def _missing_owner_token_check() -> WebPhoneCheckResult:
    return WebPhoneCheckResult(
        check_id="cloud_api_with_token",
        success=False,
        detail="owner token required for cloud API auth smoke",
    )


def _apk_check(apk_path: Path, *, min_bytes: int) -> WebPhoneCheckResult:
    started = time.perf_counter()
    if not apk_path.exists():
        return WebPhoneCheckResult(
            check_id="android_debug_apk",
            success=False,
            detail=f"APK not found at {apk_path}",
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    size = apk_path.stat().st_size
    if size < min_bytes:
        return WebPhoneCheckResult(
            check_id="android_debug_apk",
            success=False,
            detail=f"APK exists but is unexpectedly small ({size} bytes)",
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    return WebPhoneCheckResult(
        check_id="android_debug_apk",
        success=True,
        detail=f"APK exists ({size} bytes)",
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )


def _apk_web_assets_check(apk_path: Path, web_dist_dir: Path) -> WebPhoneCheckResult:
    started = time.perf_counter()
    required = ("index.html", "manifest.webmanifest", "sw.js")
    if not apk_path.exists():
        return WebPhoneCheckResult(
            check_id="android_apk_web_assets",
            success=False,
            detail=f"APK not found at {apk_path}",
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    missing_dist = [name for name in required if not (web_dist_dir / name).exists()]
    if missing_dist:
        return WebPhoneCheckResult(
            check_id="android_apk_web_assets",
            success=False,
            detail=f"web dist missing required asset(s): {', '.join(missing_dist)}",
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    try:
        with zipfile.ZipFile(apk_path) as archive:
            archive_names = set(archive.namelist())
            missing_apk = [f"assets/public/{name}" for name in required if f"assets/public/{name}" not in archive_names]
            if missing_apk:
                return WebPhoneCheckResult(
                    check_id="android_apk_web_assets",
                    success=False,
                    detail=f"APK missing bundled web asset(s): {', '.join(missing_apk)}",
                    elapsed_ms=(time.perf_counter() - started) * 1000.0,
                )
            stale: list[str] = []
            for name in required:
                apk_bytes = archive.read(f"assets/public/{name}")
                dist_bytes = (web_dist_dir / name).read_bytes()
                if hashlib.sha256(apk_bytes).hexdigest() != hashlib.sha256(dist_bytes).hexdigest():
                    stale.append(name)
    except zipfile.BadZipFile:
        return WebPhoneCheckResult(
            check_id="android_apk_web_assets",
            success=False,
            detail="APK is not a readable zip archive",
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    if stale:
        return WebPhoneCheckResult(
            check_id="android_apk_web_assets",
            success=False,
            detail=(
                "APK bundled web asset(s) differ from ui/dist: "
                f"{', '.join(stale)}; run npm run mobile:apk:debug or npm run mobile:apk:sync"
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
    return WebPhoneCheckResult(
        check_id="android_apk_web_assets",
        success=True,
        detail="APK bundled web assets match ui/dist",
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )


def run_web_phone_smoke(
    *,
    web_base: str = "http://127.0.0.1:4173",
    apk_path: str | Path = "ui/android/app/build/outputs/apk/debug/app-debug.apk",
    timeout_seconds: float = 10.0,
    check_api_proxy: bool = True,
    check_phone_proof_proxy: bool = True,
    check_cloud_api_auth: bool = False,
    owner_token: str | None = None,
    protected_api_path: str = "/api/forex/owner-auth/state",
    check_apk: bool = True,
    apk_min_bytes: int = 1_000_000,
    web_dist_dir: str | Path = "ui/dist",
    transport: Transport | None = None,
) -> WebPhoneSmokeReport:
    """Run web/phone readiness checks against a served production preview."""
    started = time.perf_counter()
    transport = transport or _default_transport
    results: list[WebPhoneCheckResult] = [
        _http_check(
            "app_shell",
            _join(web_base, "/"),
            transport=transport,
            timeout_seconds=timeout_seconds,
            validator=_index_validator,
        ),
        _http_check(
            "pwa_manifest",
            _join(web_base, "/manifest.webmanifest"),
            transport=transport,
            timeout_seconds=timeout_seconds,
            validator=_manifest_validator,
        ),
        _http_check(
            "service_worker",
            _join(web_base, "/sw.js"),
            transport=transport,
            timeout_seconds=timeout_seconds,
            validator=_service_worker_validator,
        ),
    ]
    if check_api_proxy:
        results.append(
            _http_check(
                "same_origin_api_proxy",
                _join(web_base, "/api/forex/health"),
                transport=transport,
                timeout_seconds=timeout_seconds,
                validator=_api_proxy_validator,
            )
        )
    if check_phone_proof_proxy:
        pairing_context = _pairing_context_from_pairing_payload(
            web_base=web_base,
            transport=transport,
            timeout_seconds=timeout_seconds,
        )
        phone_web_base = pairing_context.get("phone_origin") or web_base
        phone_api_base = pairing_context.get("api_base") or f"{web_base.rstrip('/')}/api/forex"
        proof_body = json.dumps(_phone_proof_proxy_dry_run_payload(phone_web_base, phone_api_base)).encode("utf-8")
        proof_headers = {
            "Content-Type": "application/json",
            "X-Forwarded-For": "10.0.0.55",
            "X-Real-IP": "10.0.0.55",
            "X-CAS-Client-API-Base": phone_api_base,
        }
        proof_owner_token = owner_token or pairing_context.get("owner_token")
        if proof_owner_token:
            proof_headers["X-CAS-Owner-Token"] = proof_owner_token
        results.append(
            _http_check(
                "phone_proof_proxy_dry_run",
                _join(web_base, "/api/forex/mobile/phone-proof"),
                method="POST",
                transport=transport,
                timeout_seconds=timeout_seconds,
                validator=_phone_proof_proxy_dry_run_validator,
                headers=proof_headers,
                body=proof_body,
                max_attempts=_PROBE_MAX_ATTEMPTS,
            )
        )
    if check_cloud_api_auth:
        results.append(
            _http_check(
                "cloud_api_without_token",
                _join(web_base, protected_api_path),
                transport=transport,
                timeout_seconds=timeout_seconds,
                validator=_protected_api_without_token_validator,
            )
        )
        if owner_token:
            results.append(
                _http_check(
                    "cloud_api_with_token",
                    _join(web_base, protected_api_path),
                    transport=transport,
                    timeout_seconds=timeout_seconds,
                    validator=_protected_api_with_token_validator,
                    headers={"X-CAS-Owner-Token": owner_token},
                )
            )
        else:
            results.append(_missing_owner_token_check())
    resolved_apk_path = Path(apk_path)
    resolved_web_dist = Path(web_dist_dir)
    if check_apk:
        results.append(_apk_check(resolved_apk_path, min_bytes=apk_min_bytes))
        results.append(_apk_web_assets_check(resolved_apk_path, resolved_web_dist))

    passed = sum(1 for result in results if result.success)
    failed = len(results) - passed
    summary = (
        "Web/phone smoke passed: installable shell, PWA assets, API proxy, and APK are ready."
        if failed == 0
        else f"Web/phone smoke has {failed} failing check(s); see per-check details."
    )
    return WebPhoneSmokeReport(
        web_base=web_base,
        apk_path=str(resolved_apk_path),
        total_checks=len(results),
        passed=passed,
        failed=failed,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        results=tuple(results),
        plain_english_summary=summary,
    )


def report_to_dict(report: WebPhoneSmokeReport) -> dict:
    out = asdict(report)
    out["results"] = [asdict(result) for result in report.results]
    return out
