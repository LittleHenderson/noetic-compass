"""Start or verify the CAS Forex mobile web stack and emit readiness evidence."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from cas_forex.mobile_release_readiness import (
    readiness_to_dict,
    render_readiness_report,
    run_mobile_release_readiness,
)
from cas_forex.mobile_web_base import default_mobile_web_base, quick_start_url
from cas_forex.runtime_topology import validate_api_worker_count


DEFAULT_API_PORT = 8765
DEFAULT_WEB_PORT = 4173
DEFAULT_OUTPUT_DIR = Path("evidence_runs") / "mobile_stack" / "latest"

UrlChecker = Callable[[str, float], bool]
ReadinessRunner = Callable[..., Any]
ProcessStarter = Callable[[Sequence[str], Path, Path], subprocess.Popen]


@dataclass(frozen=True)
class MobileStackProcess:
    name: str
    command: tuple[str, ...]
    pid: int | None
    started: bool
    log_path: str | None


@dataclass(frozen=True)
class MobileStackRunReport:
    generated_at: str
    workspace_root: str
    web_base: str
    phone_quick_start_url: str
    api_health_url: str
    web_health_url: str
    api_ready: bool
    web_ready: bool
    start_missing: bool
    keep_running: bool
    package_ready_for_phone_install: bool
    physical_phone_verified: bool
    phone_browser_observed: bool
    phone_browser_verified: bool
    docker_available: bool
    processes: tuple[MobileStackProcess, ...]
    readiness_report_path: str
    readiness_report: dict[str, Any]
    summary: str


def run_mobile_stack_readiness(
    *,
    workspace_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    web_base: str | None = None,
    api_host: str = "0.0.0.0",
    api_port: int = DEFAULT_API_PORT,
    api_workers: int = 1,
    web_host: str = "0.0.0.0",
    web_port: int = DEFAULT_WEB_PORT,
    python_executable: str | None = None,
    npm_executable: str | None = None,
    start_missing: bool = True,
    keep_running: bool = True,
    timeout_seconds: float = 45.0,
    poll_seconds: float = 0.5,
    url_checker: UrlChecker | None = None,
    readiness_runner: ReadinessRunner | None = None,
    process_starter: ProcessStarter | None = None,
) -> MobileStackRunReport:
    validate_api_worker_count(api_workers)
    root = Path(workspace_root).resolve()
    resolved_output = _resolve_under_root(root, output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    checker = url_checker or _url_ok
    starter = process_starter or _start_process
    runner = readiness_runner or run_mobile_release_readiness
    readiness_web_base = web_base or default_mobile_web_base(web_port)
    api_health_url = f"http://127.0.0.1:{api_port}/api/forex/health"
    web_health_url = f"http://127.0.0.1:{web_port}/"

    processes: list[MobileStackProcess] = []
    started_processes: list[subprocess.Popen] = []
    api_ready = checker(api_health_url, 2.0)
    if not api_ready and start_missing:
        api_command = _api_command(python_executable, api_host, api_port, api_workers)
        api_log = resolved_output / "cas-forex-api.log"
        proc = starter(api_command, root, api_log)
        started_processes.append(proc)
        processes.append(_process_report("cas-forex-api", api_command, proc, api_log, started=True))

    web_ready = checker(web_health_url, 2.0)
    if not web_ready and start_missing:
        web_command = _web_command(npm_executable, web_host, web_port)
        web_log = resolved_output / "cas-forex-mobile-preview.log"
        proc = starter(web_command, root, web_log)
        started_processes.append(proc)
        processes.append(_process_report("cas-forex-mobile-preview", web_command, proc, web_log, started=True))

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        api_ready = checker(api_health_url, 2.0)
        web_ready = checker(web_health_url, 2.0)
        if api_ready and web_ready:
            break
        time.sleep(poll_seconds)

    readiness = runner(web_base=readiness_web_base, timeout_seconds=10.0, workspace_root=root)
    readiness_payload = readiness_to_dict(readiness)
    phone_quick_start = str(
        readiness_payload.get("phone_quick_start_url")
        or getattr(readiness, "phone_quick_start_url", None)
        or quick_start_url(readiness_web_base)
    )
    readiness_path = resolved_output / "mobile_release_readiness.json"
    readiness_path.write_text(json.dumps(readiness_payload, indent=2), encoding="utf-8")

    if not keep_running:
        for proc in started_processes:
            _terminate_started_process(proc)

    summary = _summary(api_ready=api_ready, web_ready=web_ready, package_ready=bool(readiness.package_ready_for_phone_install))
    return MobileStackRunReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        workspace_root=str(root),
        web_base=readiness_web_base,
        phone_quick_start_url=phone_quick_start,
        api_health_url=api_health_url,
        web_health_url=web_health_url,
        api_ready=api_ready,
        web_ready=web_ready,
        start_missing=start_missing,
        keep_running=keep_running,
        package_ready_for_phone_install=bool(readiness.package_ready_for_phone_install),
        physical_phone_verified=bool(readiness.physical_phone_verified),
        phone_browser_observed=bool(getattr(readiness, "phone_browser_observed", False)),
        phone_browser_verified=bool(getattr(readiness, "phone_browser_verified", False)),
        docker_available=bool(readiness.docker_available),
        processes=tuple(processes),
        readiness_report_path=str(readiness_path),
        readiness_report=readiness_payload,
        summary=summary,
    )


def stack_report_to_dict(report: MobileStackRunReport) -> dict[str, Any]:
    out = asdict(report)
    out["processes"] = [asdict(process) for process in report.processes]
    return out


def render_stack_report(report: MobileStackRunReport) -> str:
    lines = [
        "CAS Forex mobile stack readiness",
        report.summary,
        "",
        f"Web base: {report.web_base}",
        f"Phone Quick Start URL: {report.phone_quick_start_url}",
        f"API ready: {str(report.api_ready).lower()} ({report.api_health_url})",
        f"Web ready: {str(report.web_ready).lower()} ({report.web_health_url})",
        f"Package ready for phone install: {str(report.package_ready_for_phone_install).lower()}",
        f"Physical phone verified: {str(report.physical_phone_verified).lower()}",
        f"Phone browser observed: {str(report.phone_browser_observed).lower()}",
        f"Phone browser verified: {str(report.phone_browser_verified).lower()}",
        f"Docker available: {str(report.docker_available).lower()}",
        f"Readiness report: {report.readiness_report_path}",
    ]
    if report.processes:
        lines.extend(["", "Processes started:"])
        for process in report.processes:
            lines.append(
                f"- {process.name}: pid={process.pid or 'unknown'} log={process.log_path or 'n/a'}"
            )
    lines.extend(["", render_readiness_report(_ReadinessView(report.readiness_report))])
    return "\n".join(lines)


def _api_command(python_executable: str | None, host: str, port: int, workers: int = 1) -> tuple[str, ...]:
    return (
        python_executable or sys.executable,
        str(Path("scripts") / "run_api_server.py"),
        "--host",
        host,
        "--port",
        str(port),
        "--workers",
        str(max(1, workers)),
    )


def _web_command(npm_executable: str | None, host: str, port: int) -> tuple[str, ...]:
    npm = npm_executable or shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    return (
        npm,
        "--prefix",
        "ui",
        "run",
        "preview",
        "--",
        "--host",
        host,
        "--port",
        str(port),
    )


def _start_process(command: Sequence[str], cwd: Path, log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("ab")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        list(command),
        cwd=str(cwd),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _process_report(
    name: str,
    command: Sequence[str],
    proc: subprocess.Popen,
    log_path: Path,
    *,
    started: bool,
) -> MobileStackProcess:
    return MobileStackProcess(
        name=name,
        command=tuple(str(part) for part in command),
        pid=getattr(proc, "pid", None),
        started=started,
        log_path=str(log_path),
    )


def _url_ok(url: str, timeout_seconds: float) -> bool:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= int(response.status) < 300
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        return False


def _terminate_started_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _summary(*, api_ready: bool, web_ready: bool, package_ready: bool) -> str:
    if api_ready and web_ready and package_ready:
        return "Mobile stack is running and the package readiness checks passed."
    if api_ready and web_ready:
        return "Mobile stack is running, but package readiness checks need attention."
    return "Mobile stack is not fully reachable; inspect started process logs and readiness checks."


class _ReadinessView:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.web_base = str(payload.get("web_base") or "")
        self.phone_quick_start_url = str(payload.get("phone_quick_start_url") or "")
        commands = payload.get("verification_commands")
        self.verification_commands = commands if isinstance(commands, dict) else {}
        self.summary = str(payload.get("summary") or "")
        self.package_ready_for_phone_install = bool(payload.get("package_ready_for_phone_install"))
        self.physical_phone_verified = bool(payload.get("physical_phone_verified"))
        self.phone_proof_checked = bool(payload.get("phone_proof_checked", True))
        self.phone_browser_observed = bool(payload.get("phone_browser_observed"))
        self.phone_browser_verified = bool(payload.get("phone_browser_verified"))
        self.phone_proof_fresh = bool(payload.get("phone_proof_fresh"))
        self.phone_proof_age_seconds = _int_or_none(payload.get("phone_proof_age_seconds"))
        self.phone_proof_expires_at = _string_or_none(payload.get("phone_proof_expires_at"))
        self.phone_observation_fresh = bool(payload.get("phone_observation_fresh"))
        self.phone_observation_age_seconds = _int_or_none(payload.get("phone_observation_age_seconds"))
        self.phone_observation_expires_at = _string_or_none(payload.get("phone_observation_expires_at"))
        apk_runtime_observation = payload.get("apk_runtime_observation")
        self.apk_runtime_observation = (
            apk_runtime_observation if isinstance(apk_runtime_observation, dict) else None
        )
        self.apk_runtime_observed = bool(payload.get("apk_runtime_observed"))
        self.apk_runtime_verified = bool(payload.get("apk_runtime_verified"))
        self.apk_runtime_fresh = bool(payload.get("apk_runtime_fresh"))
        self.apk_runtime_age_seconds = _int_or_none(payload.get("apk_runtime_age_seconds"))
        self.apk_runtime_expires_at = _string_or_none(payload.get("apk_runtime_expires_at"))
        self.android_release_signing = (
            payload.get("android_release_signing")
            if isinstance(payload.get("android_release_signing"), dict)
            else None
        )
        self.android_release_signing_ready = bool(payload.get("android_release_signing_ready"))
        self.android_release_signing_status = _string_or_none(payload.get("android_release_signing_status"))
        self.android_release_signing_detail = _string_or_none(payload.get("android_release_signing_detail"))
        self.android_release_apk_exists = bool(payload.get("android_release_apk_exists"))
        self.paired_api_bases_reachable = bool(payload.get("paired_api_bases_reachable"))
        self.paired_api_bases_status = _string_or_none(payload.get("paired_api_bases_status"))
        self.paired_api_bases_detail = _string_or_none(payload.get("paired_api_bases_detail"))
        self.docker_available = bool(payload.get("docker_available"))
        self.checks = tuple(_CheckView(check) for check in payload.get("checks") or ())
        self.remaining_external_gates = tuple(str(gate) for gate in payload.get("remaining_external_gates") or ())
        actions = payload.get("next_verification_actions")
        self.next_verification_actions = (
            tuple(action for action in actions if isinstance(action, dict))
            if isinstance(actions, Sequence) and not isinstance(actions, (str, bytes))
            else ()
        )


class _CheckView:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.check_id = str(payload.get("check_id") or "")
        self.status = str(payload.get("status") or "")
        self.success = bool(payload.get("success"))
        self.detail = str(payload.get("detail") or "")


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
