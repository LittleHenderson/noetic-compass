"""Record Docker Desktop install attempts for CAS Forex mobile readiness."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_KIND = "cas_forex_docker_desktop_install_attempt"
DEFAULT_OUTPUT_DIR = Path("evidence_runs") / "docker_desktop_install" / "latest"
DEFAULT_OUTPUT_FILE = "docker_desktop_install_attempt.json"
DOCKER_DESKTOP_WINGET_ID = "Docker.DockerDesktop"
INSTALL_COMMAND = (
    "winget",
    "install",
    "--id",
    DOCKER_DESKTOP_WINGET_ID,
    "-e",
    "--accept-package-agreements",
    "--accept-source-agreements",
    "--silent",
    "--disable-interactivity",
)
ELEVATED_INSTALL_COMMAND = ("npm", "--prefix", "ui", "run", "mobile:docker-install-elevated")
ADMIN_ELEVATION_RETURN_CODES = {-5, 4294967291}


def run_docker_desktop_install_attempt(
    *,
    workspace_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Run winget Docker Desktop install and persist a concise attempt report."""
    root = Path(workspace_root).resolve()
    output_path = _resolve_output_path(root, output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    winget_path = shutil.which("winget")
    generated_at = datetime.now(timezone.utc).isoformat()
    if not winget_path:
        report = _report(
            generated_at=generated_at,
            status="winget_unavailable",
            success=False,
            winget_path=None,
            returncode=None,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            stdout="",
            stderr="",
            detail="winget is not available, so Docker Desktop cannot be installed by this helper.",
        )
        return _write_report(output_path, report)

    command = (winget_path, *INSTALL_COMMAND[1:])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _output_text(exc.stdout)
        stderr = _output_text(exc.stderr)
        report = _report(
            generated_at=generated_at,
            status="timeout",
            success=False,
            winget_path=winget_path,
            returncode=None,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            stdout=stdout,
            stderr=stderr,
            detail=f"Docker Desktop install attempt timed out after {timeout_seconds:g} seconds.",
        )
        return _write_report(output_path, report)
    except OSError as exc:
        report = _report(
            generated_at=generated_at,
            status="install_failed",
            success=False,
            winget_path=winget_path,
            returncode=None,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            stdout="",
            stderr=f"{type(exc).__name__}: {exc}",
            detail="Docker Desktop install attempt could not launch winget.",
        )
        return _write_report(output_path, report)

    stdout = _output_text(result.stdout)
    stderr = _output_text(result.stderr)
    combined = f"{stdout}\n{stderr}"
    installer_exit_code = _installer_exit_code(combined)
    admin_required = _admin_elevation_required(result.returncode, combined, installer_exit_code=installer_exit_code)
    success = result.returncode == 0
    status = "installed_or_started" if success else "admin_elevation_required" if admin_required else "install_failed"
    detail = (
        "Docker Desktop install command completed. Restart or open Docker Desktop if the engine is still unavailable."
        if success
        else "Docker Desktop installer was reached through winget, but installation requires administrator elevation."
        if admin_required
        else f"Docker Desktop install command failed with exit code {result.returncode}."
    )
    report = _report(
        generated_at=generated_at,
        status=status,
        success=success,
        winget_path=winget_path,
        returncode=result.returncode,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        stdout=stdout,
        stderr=stderr,
        detail=detail,
    )
    report["admin_elevation_required"] = admin_required
    report["installer_exit_code"] = installer_exit_code
    return _write_report(output_path, report)


def latest_docker_desktop_install_attempt(*, workspace_root: str | Path = ".") -> dict[str, Any] | None:
    """Read the latest Docker Desktop install attempt report, if one exists."""
    root = Path(workspace_root).resolve()
    path = root / DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "report_kind": REPORT_KIND,
            "status": "EVIDENCE_UNREADABLE",
            "success": False,
            "detail": f"Docker Desktop install attempt evidence could not be read: {type(exc).__name__}.",
            "source_path": str(path),
        }
    if not isinstance(payload, dict):
        return {
            "report_kind": REPORT_KIND,
            "status": "EVIDENCE_MALFORMED",
            "success": False,
            "detail": "Docker Desktop install attempt evidence was not a JSON object.",
            "source_path": str(path),
        }
    payload.setdefault("source_path", str(path))
    return payload


def render_docker_desktop_install_attempt(report: dict[str, Any]) -> str:
    """Render a Docker Desktop install attempt for the owner."""
    lines = [
        "CAS Forex Docker Desktop install attempt",
        f"Status: {report.get('status') or 'unknown'}",
        f"Success: {str(bool(report.get('success'))).lower()}",
        f"Detail: {report.get('detail') or 'unavailable'}",
        f"Command: {report.get('install_command') or _install_command_string()}",
        f"Elevated command: {report.get('elevated_install_command') or elevated_install_command_string()}",
        f"winget path: {report.get('winget_path') or 'not found'}",
        f"Return code: {report.get('returncode') if report.get('returncode') is not None else 'unavailable'}",
        f"Installer exit code: {report.get('installer_exit_code') if report.get('installer_exit_code') is not None else 'unavailable'}",
        f"Evidence: {report.get('written_path') or report.get('source_path') or 'unavailable'}",
    ]
    stdout = _trim_output(str(report.get("stdout") or ""))
    stderr = _trim_output(str(report.get("stderr") or ""))
    if stdout:
        lines.extend(["", "stdout:", stdout])
    if stderr:
        lines.extend(["", "stderr:", stderr])
    return "\n".join(lines)


def _report(
    *,
    generated_at: str,
    status: str,
    success: bool,
    winget_path: str | None,
    returncode: int | None,
    elapsed_ms: float,
    stdout: str,
    stderr: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "generated_at": generated_at,
        "status": status,
        "success": success,
        "detail": detail,
        "install_command": _install_command_string(),
        "elevated_install_command": elevated_install_command_string(),
        "winget_path": winget_path,
        "winget_id": DOCKER_DESKTOP_WINGET_ID,
        "returncode": returncode,
        "elapsed_ms": elapsed_ms,
        "stdout": _trim_output(stdout, limit=4000),
        "stderr": _trim_output(stderr, limit=4000),
        "admin_elevation_required": status == "admin_elevation_required",
    }


def _write_report(output_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    path = output_path / DEFAULT_OUTPUT_FILE
    report = dict(report)
    report["written_path"] = str(path)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _resolve_output_path(root: Path, output_dir: str | Path) -> Path:
    path = Path(output_dir)
    return path if path.is_absolute() else root / path


def _admin_elevation_required(
    returncode: int | None,
    output: str,
    *,
    installer_exit_code: int | None = None,
) -> bool:
    normalized = output.lower()
    return (
        returncode in ADMIN_ELEVATION_RETURN_CODES
        or installer_exit_code in ADMIN_ELEVATION_RETURN_CODES
        or "request to run as administrator" in normalized
        or "requires administrator" in normalized
        or ("administrator" in normalized and "elevation" in normalized)
    )


def _installer_exit_code(output: str) -> int | None:
    match = re.search(r"installer failed with exit code:\s*(-?\d+)", output, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _install_command_string() -> str:
    return " ".join(INSTALL_COMMAND)


def elevated_install_command_string() -> str:
    return " ".join(ELEVATED_INSTALL_COMMAND)


def _output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _trim_output(value: str, *, limit: int = 1200) -> str:
    cleaned = value.replace("\x00", "").replace("\r\n", "\n").strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."
