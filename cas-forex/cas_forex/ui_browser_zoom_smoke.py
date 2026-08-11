"""Headless browser screenshot smoke checks for CAS Forex UI routes."""

from __future__ import annotations

import os
import json
import shutil
import struct
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlencode, urlsplit

from cas_forex.ui_layout_contract import REPO_ROOT, ui_registered_page_ids


REPORT_KIND = "cas_forex_ui_browser_zoom_smoke"
CLAIM_BOUNDARY = (
    "UI browser zoom smoke uses a local headless browser against the built web "
    "UI to capture screenshots and verify nonempty PNG dimensions. It is "
    "observational only: it does not call trading actions, place orders, close "
    "positions, move money, change settings, authorize live trading, or promise "
    "returns."
)

DEFAULT_PROFILES: tuple[dict[str, Any], ...] = (
    {"profile": "desktop", "width": 1280, "height": 900, "effective_zoom": "100%"},
    {"profile": "desktop_zoom_150_effective", "width": 853, "height": 600, "effective_zoom": "150%"},
    {"profile": "phone", "width": 390, "height": 844, "effective_zoom": "phone"},
)
MIN_SCREENSHOT_BYTES = 3_000


@dataclass(frozen=True)
class UIBrowserScreenshotResult:
    page: str
    profile: str
    url: str
    success: bool
    screenshot_path: str
    width: int | None = None
    height: int | None = None
    bytes: int = 0
    elapsed_ms: float = 0.0
    detail: str = ""
    command_returncode: int | None = None


@dataclass(frozen=True)
class UIBrowserZoomSmokeReport:
    report_kind: str
    status: str
    browser_path: str | None
    served_base_url: str | None
    output_dir: str
    report_path: str | None
    page_count: int
    profile_count: int
    screenshot_count: int
    passed: int
    failed: int
    elapsed_ms: float
    screenshots: tuple[UIBrowserScreenshotResult, ...]
    top_attention_items: tuple[str, ...]
    dry_run: bool
    claim_boundary: str


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        return

    def do_GET(self) -> None:
        if urlsplit(self.path).path.startswith("/api/"):
            body = json.dumps(
                {
                    "status": "offline_static_ui_smoke",
                    "detail": "Static screenshot server does not proxy API calls.",
                }
            ).encode("utf-8")
            self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return
            return
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return


def run_ui_browser_zoom_smoke(
    *,
    root: Path | str | None = None,
    dist_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    pages: Sequence[str] | None = None,
    profiles: Sequence[str] | None = None,
    browser_path: str | Path | None = None,
    timeout_seconds: float = 25.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Serve ``ui/dist`` locally and capture browser screenshots for UI pages."""
    started = time.perf_counter()
    base = Path(root) if root is not None else REPO_ROOT
    resolved_dist = Path(dist_dir) if dist_dir is not None else base / "ui" / "dist"
    requested_pages = _select_pages(base, pages)
    selected_profiles = _select_profiles(profiles)
    resolved_output = _resolve_output_dir(base, output_dir)
    browser = str(browser_path) if browser_path else _find_browser()

    if dry_run:
        screenshots = tuple(
            UIBrowserScreenshotResult(
                page=page,
                profile=profile["profile"],
                url=_page_url("http://127.0.0.1:0", page),
                success=True,
                screenshot_path=str(resolved_output / f"{_safe_name(page)}__{profile['profile']}.png"),
                width=int(profile["width"]),
                height=int(profile["height"]),
                detail="planned",
            )
            for page in requested_pages
            for profile in selected_profiles
        )
        return _report_to_dict(
            UIBrowserZoomSmokeReport(
                report_kind=REPORT_KIND,
                status="DRY_RUN",
                browser_path=browser,
                served_base_url=None,
                output_dir=str(resolved_output),
                report_path=None,
                page_count=len(requested_pages),
                profile_count=len(selected_profiles),
                screenshot_count=len(screenshots),
                passed=len(screenshots),
                failed=0,
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                screenshots=screenshots,
                top_attention_items=(),
                dry_run=True,
                claim_boundary=CLAIM_BOUNDARY,
            )
        )

    attention: list[str] = []
    if not browser:
        attention.append("No Chrome/Edge browser executable was found.")
    if not (resolved_dist / "index.html").exists():
        attention.append(f"Built UI not found at {resolved_dist}; run npm --prefix ui run build first.")
    if attention:
        return _report_to_dict(
            UIBrowserZoomSmokeReport(
                report_kind=REPORT_KIND,
                status="ATTENTION",
                browser_path=browser,
                served_base_url=None,
                output_dir=str(resolved_output),
                report_path=None,
                page_count=len(requested_pages),
                profile_count=len(selected_profiles),
                screenshot_count=0,
                passed=0,
                failed=len(attention),
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                screenshots=(),
                top_attention_items=tuple(attention),
                dry_run=False,
                claim_boundary=CLAIM_BOUNDARY,
            )
        )

    resolved_output.mkdir(parents=True, exist_ok=True)
    server = _StaticServer(resolved_dist)
    server.start()
    try:
        screenshots = tuple(
            _capture_screenshot(
                browser=browser,
                base_url=server.base_url,
                output_dir=resolved_output,
                page=page,
                profile=profile,
                timeout_seconds=timeout_seconds,
            )
            for page in requested_pages
            for profile in selected_profiles
        )
    finally:
        server.stop()

    failed = tuple(result for result in screenshots if not result.success)
    report_path = resolved_output / "ui_browser_zoom_smoke_report.json"
    return _write_report(
        UIBrowserZoomSmokeReport(
            report_kind=REPORT_KIND,
            status="OK" if not failed else "ATTENTION",
            browser_path=browser,
            served_base_url=server.base_url,
            output_dir=str(resolved_output),
            report_path=str(report_path),
            page_count=len(requested_pages),
            profile_count=len(selected_profiles),
            screenshot_count=len(screenshots),
            passed=len(screenshots) - len(failed),
            failed=len(failed),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            screenshots=screenshots,
            top_attention_items=tuple(result.detail for result in failed[:8]),
            dry_run=False,
            claim_boundary=CLAIM_BOUNDARY,
        ),
        report_path,
    )


class _StaticServer:
    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.base_url: str | None = None

    def start(self) -> None:
        handler = partial(_QuietHandler, directory=str(self._directory))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        host, port = self._server.server_address
        self.base_url = f"http://{host}:{port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5.0)


def _capture_screenshot(
    *,
    browser: str,
    base_url: str,
    output_dir: Path,
    page: str,
    profile: dict[str, Any],
    timeout_seconds: float,
) -> UIBrowserScreenshotResult:
    started = time.perf_counter()
    screenshot_path = output_dir / f"{_safe_name(page)}__{profile['profile']}.png"
    url = _page_url(base_url, page)
    with tempfile.TemporaryDirectory(prefix="cas-ui-browser-") as user_data:
        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            f"--user-data-dir={user_data}",
            f"--window-size={int(profile['width'])},{int(profile['height'])}",
            "--virtual-time-budget=4500",
            f"--screenshot={screenshot_path}",
            url,
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return UIBrowserScreenshotResult(
                page=page,
                profile=str(profile["profile"]),
                url=url,
                success=False,
                screenshot_path=str(screenshot_path),
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                detail=f"Timed out after {timeout_seconds:g}s: {exc}",
            )

    width, height = _png_size(screenshot_path)
    size = screenshot_path.stat().st_size if screenshot_path.exists() else 0
    expected_width = int(profile["width"])
    expected_height = int(profile["height"])
    success = (
        completed.returncode == 0
        and width == expected_width
        and height == expected_height
        and size >= MIN_SCREENSHOT_BYTES
    )
    detail = "screenshot captured"
    if completed.returncode != 0:
        detail = f"browser exited {completed.returncode}: {(completed.stderr or completed.stdout).strip()[:240]}"
    elif width != expected_width or height != expected_height:
        detail = f"unexpected screenshot dimensions {width}x{height}, expected {expected_width}x{expected_height}"
    elif size < MIN_SCREENSHOT_BYTES:
        detail = f"screenshot too small ({size} bytes), likely blank or failed render"
    return UIBrowserScreenshotResult(
        page=page,
        profile=str(profile["profile"]),
        url=url,
        success=success,
        screenshot_path=str(screenshot_path),
        width=width,
        height=height,
        bytes=size,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        detail=detail,
        command_returncode=completed.returncode,
    )


def _select_pages(base: Path, pages: Sequence[str] | None) -> tuple[str, ...]:
    registered = ui_registered_page_ids(base)
    if not pages:
        return registered
    normalized = tuple(page.strip() for page in pages if page.strip())
    if normalized == ("all",):
        return registered
    unknown = sorted(set(normalized) - set(registered))
    if unknown:
        raise ValueError(f"Unknown page id(s): {', '.join(unknown)}")
    return normalized


def _select_profiles(profiles: Sequence[str] | None) -> tuple[dict[str, Any], ...]:
    if not profiles:
        return DEFAULT_PROFILES
    requested = tuple(profile.strip() for profile in profiles if profile.strip())
    if requested == ("all",):
        return DEFAULT_PROFILES
    by_name = {str(profile["profile"]): profile for profile in DEFAULT_PROFILES}
    unknown = sorted(set(requested) - set(by_name))
    if unknown:
        raise ValueError(f"Unknown profile(s): {', '.join(unknown)}")
    return tuple(by_name[name] for name in requested)


def _resolve_output_dir(base: Path, output_dir: Path | str | None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return base / "runtime" / "ui_browser_zoom_smoke" / stamp


def _find_browser() -> str | None:
    env_path = os.environ.get("CAS_FOREX_BROWSER_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe", "chromium", "chromium.exe"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _page_url(base_url: str, page: str) -> str:
    return f"{base_url}/?{urlencode({'page': page})}"


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _png_size(path: Path) -> tuple[int | None, int | None]:
    if not path.exists() or path.stat().st_size < 24:
        return None, None
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None, None
    return struct.unpack(">II", data[16:24])


def _report_to_dict(report: UIBrowserZoomSmokeReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["screenshots"] = [asdict(item) for item in report.screenshots]
    payload["top_attention_items"] = list(report.top_attention_items)
    return payload


def _write_report(report: UIBrowserZoomSmokeReport, report_path: Path) -> dict[str, Any]:
    payload = _report_to_dict(report)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
